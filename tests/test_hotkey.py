"""Unit tests for HotkeyListener key-state logic (no pynput I/O)."""
import sys, types

# Stub pynput so tests run without the real device layer
pynput_mod = types.ModuleType("pynput")
keyboard_mod = types.ModuleType("pynput.keyboard")

class _Key:
    ctrl   = "ctrl"
    ctrl_l = "ctrl_l"
    ctrl_r = "ctrl_r"
    cmd    = "cmd"
    cmd_l  = "cmd_l"
    cmd_r  = "cmd_r"

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

from hotkey_listener import HotkeyListener


def test_both_keys_triggers_press_callback():
    pressed = []
    released = []
    hl = HotkeyListener(on_press_cb=lambda: pressed.append(1),
                        on_release_cb=lambda: released.append(1))
    hl.start()
    hl._on_key_press("ctrl_l")
    assert pressed == [], "should not fire on ctrl alone"
    hl._on_key_press("cmd")
    assert pressed == [1], "should fire when both ctrl+win held"
    assert released == []


def test_release_triggers_release_callback():
    pressed = []
    released = []
    hl = HotkeyListener(on_press_cb=lambda: pressed.append(1),
                        on_release_cb=lambda: released.append(1))
    hl.start()
    hl._on_key_press("ctrl_l")
    hl._on_key_press("cmd")
    hl._on_key_release("ctrl_l")
    assert released == [1]


def test_no_double_fire_on_repeat_press():
    pressed = []
    hl = HotkeyListener(on_press_cb=lambda: pressed.append(1),
                        on_release_cb=lambda: None)
    hl.start()
    hl._on_key_press("ctrl_l")
    hl._on_key_press("cmd")
    hl._on_key_press("cmd")   # key repeat — should not re-fire
    assert pressed == [1]


def test_no_spurious_release_without_active():
    released = []
    hl = HotkeyListener(on_press_cb=lambda: None,
                        on_release_cb=lambda: released.append(1))
    hl.start()
    hl._on_key_release("ctrl_l")   # release without ever pressing both
    assert released == []
