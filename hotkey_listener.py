"""Global configurable push-to-talk hotkey listener using pynput.

Fixes the stuck-key bug where Windows swallows Win-key release events by
verifying real-time OS key state via GetAsyncKeyState before activating.
"""
import ctypes
import sys

from pynput import keyboard

# ── Win32 Virtual-Key codes ───────────────────────────────────────────
_VK_MAP = {
    "ctrl":   [0x11],            # VK_CONTROL
    "shift":  [0x10],            # VK_SHIFT
    "alt":    [0x12],            # VK_MENU
    "win":    [0x5B, 0x5C],      # VK_LWIN, VK_RWIN
    "tab":    [0x09],
    "space":  [0x20],
    "escape": [0x1B],
    "delete": [0x2E],
    "period": [0xBE],
}
# F1–F12
for _i in range(1, 13):
    _VK_MAP[f"f{_i}"] = [0x6F + _i]          # VK_F1 = 0x70
# A–Z
for _c in range(26):
    _VK_MAP[chr(ord("a") + _c)] = [0x41 + _c]
# 0–9
for _d in range(10):
    _VK_MAP[str(_d)] = [0x30 + _d]

# ── pynput Key objects for modifiers ──────────────────────────────────
_MODIFIER_KEYS = {
    "ctrl":  ("ctrl", "ctrl_l", "ctrl_r"),
    "shift": ("shift", "shift_l", "shift_r"),
    "alt":   ("alt", "alt_l", "alt_r", "alt_gr"),
    "win":   ("cmd", "cmd_l", "cmd_r"),
}


def _pynput_key_objects(name: str):
    """Return the set of pynput Key enum members that match *name*."""
    k = keyboard.Key
    if name in _MODIFIER_KEYS:
        return {getattr(k, a, None) for a in _MODIFIER_KEYS[name]} - {None}
    # Special named keys
    special = {
        "tab": {k.tab}, "space": {k.space}, "escape": {k.esc},
        "delete": {k.delete}, "period": set(),
    }
    if name in special:
        return special[name]
    # F-keys
    if name.startswith("f") and name[1:].isdigit():
        obj = getattr(k, name, None)
        return {obj} if obj else set()
    # Regular character — matched via KeyCode
    return set()


def _is_on_windows() -> bool:
    return sys.platform == "win32"


def _is_key_physically_pressed(vk: int) -> bool:
    """Check whether a virtual key is currently held via Win32 API."""
    return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)


def format_combo(combo: list[str]) -> str:
    """Human-readable label, e.g. ['ctrl', 'win'] → 'Ctrl + Win'."""
    names = {"ctrl": "Ctrl", "shift": "Shift", "alt": "Alt", "win": "Win"}
    return " + ".join(names.get(k, k.upper()) for k in combo)


class HotkeyListener:
    """Configurable global hotkey. Hold to activate, release to deactivate.

    Parameters
    ----------
    combo : list[str]
        Key identifiers, e.g. ``["ctrl", "win"]`` or ``["ctrl", "shift", "f9"]``.
    on_press_cb, on_release_cb : callable
        Fired on activation / deactivation (from the listener thread).
    """

    def __init__(self, combo: list[str], on_press_cb, on_release_cb):
        self._combo = [k.lower() for k in combo]
        self._on_press_cb = on_press_cb
        self._on_release_cb = on_release_cb
        self._active = False
        self._listener = None

        # Build lookup structures for the configured combo
        self._held: dict[str, bool] = {k: False for k in self._combo}
        self._pynput_map: dict[str, set] = {}  # key_name → set of pynput Key objects
        self._vk_map: dict[str, list[int]] = {}  # key_name → list of VK codes
        for k in self._combo:
            self._pynput_map[k] = _pynput_key_objects(k)
            self._vk_map[k] = _VK_MAP.get(k, [])

    # ── Lifecycle ─────────────────────────────────────────────────────

    def start(self):
        self._listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None

    # ── Key matching ──────────────────────────────────────────────────

    def _match(self, key) -> str | None:
        """Return the combo-key name that *key* belongs to, or None."""
        for name, pynput_objs in self._pynput_map.items():
            if key in pynput_objs:
                return name
            # Fallback: string comparison for edge cases
            key_str = str(key).strip("'")
            if name in _MODIFIER_KEYS:
                if key_str in _MODIFIER_KEYS[name]:
                    return name
            elif key_str == name:
                return name
            # KeyCode character match
            if hasattr(key, "char") and key.char and key.char.lower() == name:
                return name
        return None

    def _all_held(self) -> bool:
        return all(self._held.values())

    def _verify_os_state(self) -> bool:
        """Use GetAsyncKeyState to confirm all combo keys are physically held."""
        if not _is_on_windows():
            return True  # can't verify on non-Windows; trust pynput state
        for name in self._combo:
            vk_codes = self._vk_map.get(name, [])
            if not vk_codes:
                continue
            if not any(_is_key_physically_pressed(vk) for vk in vk_codes):
                return False
        return True

    def _reconcile_state(self):
        """Sync tracked state with actual OS key state to fix drift."""
        if not _is_on_windows():
            return
        for name in self._combo:
            vk_codes = self._vk_map.get(name, [])
            if not vk_codes:
                continue
            self._held[name] = any(_is_key_physically_pressed(vk) for vk in vk_codes)

    # ── Event handlers ────────────────────────────────────────────────

    def _on_key_press(self, key):
        matched = self._match(key)
        if matched:
            self._held[matched] = True

        if self._all_held() and not self._active:
            if self._verify_os_state():
                self._active = True
                self._on_press_cb()
            else:
                self._reconcile_state()

    def _on_key_release(self, key):
        matched = self._match(key)
        if matched:
            self._held[matched] = False

        if self._active and not self._all_held():
            self._active = False
            self._on_release_cb()
