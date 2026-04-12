"""Yerrrp — persistent user settings backed by a JSON file."""
import json
import os
from pathlib import Path

_SETTINGS_DIR = Path.home() / ".yerrrp"
_SETTINGS_FILE = _SETTINGS_DIR / "settings.json"

_DEFAULTS = {
    "hotkey": ["ctrl", "win"],
    "model": "base",
}

# ── Known Windows system hotkeys ──────────────────────────────────────
# Mapped as frozenset → description so order doesn't matter.
WINDOWS_SYSTEM_HOTKEYS: dict[frozenset[str], str] = {
    frozenset(("ctrl", "alt", "delete")): "Windows Security Screen",
    frozenset(("win", "l")): "Lock Screen",
    frozenset(("win", "d")): "Show Desktop",
    frozenset(("win", "e")): "File Explorer",
    frozenset(("win", "r")): "Run Dialog",
    frozenset(("win", "i")): "Windows Settings",
    frozenset(("win", "s")): "Windows Search",
    frozenset(("win", "tab")): "Task View",
    frozenset(("win", "shift", "s")): "Snipping Tool",
    frozenset(("win", "a")): "Action Center",
    frozenset(("win", "x")): "Quick Link Menu",
    frozenset(("win", "p")): "Projection Settings",
    frozenset(("win", "k")): "Connect Devices",
    frozenset(("win", "v")): "Clipboard History",
    frozenset(("win", "period")): "Emoji Panel",
    frozenset(("alt", "tab")): "Window Switcher",
    frozenset(("alt", "f4")): "Close Window",
    frozenset(("ctrl", "shift", "escape")): "Task Manager",
    frozenset(("ctrl", "c")): "Copy",
    frozenset(("ctrl", "v")): "Paste",
    frozenset(("ctrl", "x")): "Cut",
    frozenset(("ctrl", "z")): "Undo",
    frozenset(("ctrl", "a")): "Select All",
    frozenset(("ctrl", "s")): "Save",
    frozenset(("ctrl", "shift", "tab")): "Previous Tab",
    frozenset(("ctrl", "tab")): "Next Tab",
    frozenset(("ctrl", "w")): "Close Tab",
}


def check_conflicts(combo: list[str]) -> str | None:
    """Return a description of the conflicting system hotkey, or None."""
    key = frozenset(combo)
    return WINDOWS_SYSTEM_HOTKEYS.get(key)


def _ensure_dir():
    _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)


def load() -> dict:
    """Load settings from disk, filling in defaults for missing keys."""
    data = dict(_DEFAULTS)
    if _SETTINGS_FILE.exists():
        try:
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                stored = json.load(f)
            data.update(stored)
        except (json.JSONDecodeError, OSError):
            pass
    return data


def save(data: dict):
    """Write settings to disk."""
    _ensure_dir()
    with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get(key: str, default=None):
    return load().get(key, default)


def set_val(key: str, value):
    data = load()
    data[key] = value
    save(data)
