"""Unit tests for HotkeyListener key-state logic (no pynput I/O)."""
import sys
import types
from unittest.mock import patch

# ── Stub pynput so tests run without the real device layer ────────────
pynput_mod = types.ModuleType("pynput")
keyboard_mod = types.ModuleType("pynput.keyboard")


class _Key:
    ctrl   = "ctrl"
    ctrl_l = "ctrl_l"
    ctrl_r = "ctrl_r"
    cmd    = "cmd"
    cmd_l  = "cmd_l"
    cmd_r  = "cmd_r"
    shift  = "shift"
    shift_l = "shift_l"
    shift_r = "shift_r"
    alt    = "alt"
    alt_l  = "alt_l"
    alt_r  = "alt_r"
    alt_gr = "alt_gr"
    tab    = "tab"
    space  = "space"
    esc    = "esc"
    delete = "delete"
    f1 = "f1"; f2 = "f2"; f3 = "f3"; f4 = "f4"
    f5 = "f5"; f6 = "f6"; f7 = "f7"; f8 = "f8"
    f9 = "f9"; f10 = "f10"; f11 = "f11"; f12 = "f12"


class _FakeListener:
    def __init__(self, on_press=None, on_release=None):
        self.on_press = on_press
        self.on_release = on_release
        self.daemon = False
    def start(self): pass
    def stop(self): pass


keyboard_mod.Key = _Key()
keyboard_mod.Listener = _FakeListener
pynput_mod.keyboard = keyboard_mod
sys.modules["pynput"] = pynput_mod
sys.modules["pynput.keyboard"] = keyboard_mod

from hotkey_listener import HotkeyListener, format_combo  # noqa: E402
from settings import check_conflicts  # noqa: E402


# ── Helper: always bypass OS key verification in tests ────────────────
def _make_listener(combo, pressed=None, released=None):
    p = pressed if pressed is not None else []
    r = released if released is not None else []
    hl = HotkeyListener(
        combo=combo,
        on_press_cb=lambda: p.append(1),
        on_release_cb=lambda: r.append(1),
    )
    hl.start()
    # Patch _verify_os_state to always return True in tests
    hl._verify_os_state = lambda: True
    return hl


# ── Original tests (adapted for configurable API) ────────────────────

def test_both_keys_triggers_press_callback():
    pressed, released = [], []
    hl = _make_listener(["ctrl", "win"], pressed, released)
    hl._on_key_press("ctrl_l")
    assert pressed == [], "should not fire on ctrl alone"
    hl._on_key_press("cmd")
    assert pressed == [1], "should fire when both ctrl+win held"
    assert released == []


def test_release_triggers_release_callback():
    pressed, released = [], []
    hl = _make_listener(["ctrl", "win"], pressed, released)
    hl._on_key_press("ctrl_l")
    hl._on_key_press("cmd")
    hl._on_key_release("ctrl_l")
    assert released == [1]


def test_no_double_fire_on_repeat_press():
    pressed = []
    hl = _make_listener(["ctrl", "win"], pressed)
    hl._on_key_press("ctrl_l")
    hl._on_key_press("cmd")
    hl._on_key_press("cmd")   # key repeat
    assert pressed == [1]


def test_no_spurious_release_without_active():
    released = []
    hl = _make_listener(["ctrl", "win"], released=released)
    hl._on_key_release("ctrl_l")
    assert released == []


# ── New: configurable combo tests ────────────────────────────────────

def test_ctrl_shift_combo():
    pressed = []
    hl = _make_listener(["ctrl", "shift"], pressed)
    hl._on_key_press("ctrl_l")
    assert pressed == []
    hl._on_key_press("shift_l")
    assert pressed == [1]


def test_alt_shift_combo():
    pressed = []
    hl = _make_listener(["alt", "shift"], pressed)
    hl._on_key_press("alt_l")
    assert pressed == []
    hl._on_key_press("shift_r")
    assert pressed == [1]


def test_three_key_combo():
    pressed = []
    hl = _make_listener(["ctrl", "alt", "shift"], pressed)
    hl._on_key_press("ctrl_l")
    assert pressed == []
    hl._on_key_press("alt_l")
    assert pressed == []
    hl._on_key_press("shift_l")
    assert pressed == [1]


def test_ctrl_alone_does_not_trigger_ctrl_win():
    """Regression test: Ctrl alone must NOT trigger the Ctrl+Win hotkey."""
    pressed = []
    hl = _make_listener(["ctrl", "win"], pressed)
    hl._on_key_press("ctrl_l")
    hl._on_key_release("ctrl_l")
    hl._on_key_press("ctrl_r")
    hl._on_key_release("ctrl_r")
    assert pressed == [], "ctrl alone must never fire the ctrl+win hotkey"


# ── New: OS state verification tests ─────────────────────────────────

def test_verify_os_state_blocks_stale_win_key():
    """If _verify_os_state returns False, hotkey must not activate."""
    pressed = []
    hl = HotkeyListener(
        combo=["ctrl", "win"],
        on_press_cb=lambda: pressed.append(1),
        on_release_cb=lambda: None,
    )
    hl.start()
    # Simulate stale win key: pynput says held, OS says not
    hl._verify_os_state = lambda: False
    hl._reconcile_state = lambda: setattr(hl, '_held', {"ctrl": True, "win": False})

    hl._on_key_press("cmd")   # win "pressed"
    hl._on_key_press("ctrl_l")  # ctrl pressed — both "held" per pynput
    # But OS verification says no → should NOT fire
    assert pressed == [], "must not fire when OS says win is not actually held"


# ── New: format_combo tests ──────────────────────────────────────────

def test_format_combo():
    assert format_combo(["ctrl", "win"]) == "Ctrl + Win"
    assert format_combo(["ctrl", "shift", "f9"]) == "Ctrl + Shift + F9"
    assert format_combo(["alt", "a"]) == "Alt + A"


# ── New: conflict detection tests ────────────────────────────────────

def test_conflict_detected():
    assert check_conflicts(["win", "l"]) == "Lock Screen"
    assert check_conflicts(["alt", "f4"]) == "Close Window"


def test_no_conflict_for_safe_combo():
    assert check_conflicts(["ctrl", "win"]) is None
    assert check_conflicts(["ctrl", "shift", "f9"]) is None
