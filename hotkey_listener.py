"""Global Ctrl+Win push-to-talk listener using pynput."""
from pynput import keyboard


class HotkeyListener:
    """Calls on_press_cb when Ctrl+Win are both held, on_release_cb when either is released."""

    def __init__(self, on_press_cb, on_release_cb):
        self._on_press_cb = on_press_cb
        self._on_release_cb = on_release_cb
        self._ctrl_held = False
        self._win_held = False
        self._active = False
        self._listener = None

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

    def _is_ctrl(self, key):
        k = keyboard.Key
        return key in (k.ctrl, k.ctrl_l, k.ctrl_r) or str(key) in ("ctrl", "ctrl_l", "ctrl_r")

    def _is_win(self, key):
        k = keyboard.Key
        return key in (k.cmd, k.cmd_l, k.cmd_r) or str(key) in ("cmd", "cmd_l", "cmd_r")

    def _on_key_press(self, key):
        if self._is_ctrl(key):
            self._ctrl_held = True
        elif self._is_win(key):
            self._win_held = True

        if self._ctrl_held and self._win_held and not self._active:
            self._active = True
            self._on_press_cb()

    def _on_key_release(self, key):
        if self._is_ctrl(key):
            self._ctrl_held = False
        elif self._is_win(key):
            self._win_held = False

        if self._active and (not self._ctrl_held or not self._win_held):
            self._active = False
            self._on_release_cb()
