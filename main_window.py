"""Yerrrp main window — Bold & Vivid redesign."""
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

from theme import (
    BG_ROOT, BG_CARD, BG_SURFACE, BG_INPUT, ACCENT_1, ACCENT_2, ACCENT_BORDER,
    DANGER, SUCCESS, WARNING, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_BOLD, FONT_NORMAL, FONT_SMALL, FONT_LABEL,
)
from hotkey_listener import format_combo, _MODIFIER_KEYS, _VK_MAP
from settings import check_conflicts

WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]
DEFAULT_MODEL  = "base"


class MainWindow(tk.Tk):
    """Main application window. Closing hides to system tray."""

    def __init__(self, app):
        super().__init__()
        self.app = app

        self.title("Yerrrp")
        self.geometry("580x460")
        self.minsize(420, 320)
        self.config(bg=BG_ROOT)

        self.protocol("WM_DELETE_WINDOW", self._hide_to_tray)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self._build_header()
        self._build_controls()
        self._build_hotkey_bar()
        self._build_status()
        self._build_log()

    def _build_header(self):
        hdr = tk.Frame(self, bg=BG_CARD, pady=10)
        hdr.pack(fill="x")

        tk.Label(hdr, text="🎙", bg=BG_CARD, fg=ACCENT_2,
                 font=("Segoe UI", 20)).pack(side="left", padx=(16, 8))

        tk.Label(hdr, text="Y E R R R P", bg=BG_CARD, fg=TEXT_PRIMARY,
                 font=(FONT_TITLE[0], 15, "bold")).pack(side="left")

        # Model selector
        model_frame = tk.Frame(hdr, bg=BG_CARD)
        model_frame.pack(side="right", padx=16)
        tk.Label(model_frame, text="MODEL", bg=BG_CARD, fg=TEXT_MUTED,
                 font=FONT_LABEL).pack(side="left", padx=(0, 6))

        self._model_var = tk.StringVar(value=DEFAULT_MODEL)
        model_menu = tk.OptionMenu(model_frame, self._model_var, *WHISPER_MODELS)
        model_menu.config(
            bg=BG_SURFACE, fg=TEXT_PRIMARY,
            activebackground=ACCENT_1, activeforeground=TEXT_PRIMARY,
            highlightthickness=0, bd=0, font=FONT_SMALL, relief="flat", padx=8,
        )
        model_menu["menu"].config(
            bg=BG_SURFACE, fg=TEXT_PRIMARY,
            activebackground=ACCENT_1, activeforeground=TEXT_PRIMARY,
        )
        model_menu.pack(side="left")

        tk.Frame(self, bg=ACCENT_BORDER, height=1).pack(fill="x")

    def _build_controls(self):
        bar = tk.Frame(self, bg=BG_ROOT, pady=10)
        bar.pack(fill="x", padx=14)

        self._rec_btn = self._btn(bar, "⏺  Record", ACCENT_1, self._toggle_record)
        self._rec_btn.pack(side="left", padx=(0, 8))

        self._ptt_btn = self._toggle_btn(bar, "PTT")
        self._ptt_btn.pack(side="left", padx=(0, 6))
        self._ptt_btn.config(command=self._toggle_ptt)

        self._vibe_btn = self._toggle_btn(bar, "✦ Vibe")
        self._vibe_btn.pack(side="left", padx=(0, 6))
        self._vibe_btn.config(command=self._toggle_vibe)

        self._btn(bar, "Copy All", BG_SURFACE, self._copy_all).pack(side="left", padx=(0, 6))
        self._btn(bar, "Clear",    BG_SURFACE, self._clear_log).pack(side="left")

        self._ptt_active  = False
        self._vibe_active = False

    def _build_hotkey_bar(self):
        bar = tk.Frame(self, bg=BG_ROOT, pady=2)
        bar.pack(fill="x", padx=14)

        tk.Label(bar, text="HOTKEY", bg=BG_ROOT, fg=TEXT_MUTED,
                 font=FONT_LABEL).pack(side="left", padx=(0, 6))

        self._hotkey_label = tk.Label(
            bar, text="", bg=BG_SURFACE, fg=TEXT_PRIMARY,
            font=FONT_SMALL, padx=10, pady=4, relief="flat",
        )
        self._hotkey_label.pack(side="left", padx=(0, 6))

        self._hotkey_change_btn = self._btn(bar, "Change", BG_SURFACE, self._start_hotkey_capture)
        self._hotkey_change_btn.pack(side="left", padx=(0, 6))

        self._hotkey_cancel_btn = self._btn(bar, "Cancel", BG_SURFACE, self._cancel_hotkey_capture)
        # Hidden until capture mode

        self._hotkey_warn = tk.Label(bar, text="", bg=BG_ROOT, fg=WARNING, font=FONT_LABEL)
        self._hotkey_warn.pack(side="left", padx=(6, 0))

        self._capturing_hotkey = False
        self._captured_keys: set[str] = set()
        self._capture_bind_id = None

    def set_hotkey_display(self, combo: list[str]):
        """Update the hotkey label to show the current combo."""
        self._hotkey_label.config(text=format_combo(combo))

    def _start_hotkey_capture(self):
        self._capturing_hotkey = True
        self._captured_keys = set()
        self._hotkey_label.config(text="Press new hotkey...", fg=ACCENT_2)
        self._hotkey_warn.config(text="")
        self._hotkey_change_btn.pack_forget()
        self._hotkey_cancel_btn.pack(side="left", padx=(0, 6))
        # Bind keyboard events on the root window
        self._capture_bind_id = self.bind_all("<KeyPress>", self._on_capture_key)
        self.bind_all("<KeyRelease>", self._on_capture_release)

    def _cancel_hotkey_capture(self):
        self._capturing_hotkey = False
        self._captured_keys = set()
        if self._capture_bind_id:
            self.unbind_all("<KeyPress>")
            self.unbind_all("<KeyRelease>")
            self._capture_bind_id = None
        self._hotkey_cancel_btn.pack_forget()
        self._hotkey_change_btn.pack(side="left", padx=(0, 6))
        self._hotkey_label.config(fg=TEXT_PRIMARY)
        self._hotkey_warn.config(text="")
        # Restore current combo display
        if hasattr(self.app, 'get_hotkey_combo'):
            self.set_hotkey_display(self.app.get_hotkey_combo())

    def _normalize_tk_key(self, event) -> str | None:
        """Convert a tkinter key event to our canonical key name."""
        sym = event.keysym.lower()
        mapping = {
            "control_l": "ctrl", "control_r": "ctrl",
            "shift_l": "shift", "shift_r": "shift",
            "alt_l": "alt", "alt_r": "alt",
            "win_l": "win", "win_r": "win",
            "super_l": "win", "super_r": "win",
            "escape": "escape", "tab": "tab", "space": "space",
            "delete": "delete",
        }
        if sym in mapping:
            return mapping[sym]
        # F-keys
        if sym.startswith("f") and sym[1:].isdigit():
            return sym
        # Single character
        if len(sym) == 1 and sym.isalnum():
            return sym
        return None

    def _on_capture_key(self, event):
        if not self._capturing_hotkey:
            return
        name = self._normalize_tk_key(event)
        if name:
            self._captured_keys.add(name)
            self._hotkey_label.config(text=format_combo(sorted(self._captured_keys)))
        return "break"

    def _on_capture_release(self, event):
        if not self._capturing_hotkey:
            return
        if not self._captured_keys:
            return
        # When any key is released, finalize the captured combo
        combo = sorted(self._captured_keys, key=lambda k: (
            0 if k == "ctrl" else 1 if k == "alt" else 2 if k == "shift" else 3 if k == "win" else 4
        ))
        if len(combo) < 2:
            self._hotkey_warn.config(text="Need at least 2 keys")
            self._captured_keys = set()
            self._hotkey_label.config(text="Press new hotkey...")
            return "break"

        # Check for unsupported keys
        for k in combo:
            if k not in _VK_MAP:
                self._hotkey_warn.config(text=f"Unsupported key: {k}")
                self._captured_keys = set()
                self._hotkey_label.config(text="Press new hotkey...")
                return "break"

        # Check for system conflicts
        conflict = check_conflicts(combo)
        if conflict:
            self._hotkey_warn.config(text=f"Conflicts with: {conflict}")
            resp = messagebox.askyesno(
                "Hotkey Conflict",
                f"The hotkey {format_combo(combo)} conflicts with "
                f"'{conflict}'.\n\nThe system shortcut may take priority "
                f"and Yerrrp's hotkey might not work reliably.\n\n"
                f"Use this hotkey anyway?",
            )
            if not resp:
                self._captured_keys = set()
                self._hotkey_label.config(text="Press new hotkey...")
                self._hotkey_warn.config(text="")
                return "break"
            self._hotkey_warn.config(text=f"Warning: conflicts with {conflict}")

        # Accept the combo
        self._capturing_hotkey = False
        self.unbind_all("<KeyPress>")
        self.unbind_all("<KeyRelease>")
        self._capture_bind_id = None
        self._hotkey_cancel_btn.pack_forget()
        self._hotkey_change_btn.pack(side="left", padx=(0, 6))
        self._hotkey_label.config(fg=TEXT_PRIMARY)
        self.set_hotkey_display(combo)

        # Notify the app to apply the new hotkey
        if hasattr(self.app, 'change_hotkey'):
            self.app.change_hotkey(combo)

        return "break"

    def _build_status(self):
        self._status_var = tk.StringVar(value="Ready")
        bar = tk.Frame(self, bg=BG_SURFACE, pady=4)
        bar.pack(fill="x", padx=14)
        tk.Label(bar, textvariable=self._status_var, bg=BG_SURFACE,
                 fg=TEXT_SECONDARY, font=FONT_SMALL, anchor="w").pack(fill="x", padx=10)

    def _build_log(self):
        frame = tk.Frame(self, bg=BG_ROOT)
        frame.pack(fill="both", expand=True, padx=14, pady=(8, 12))

        sb = tk.Scrollbar(frame, bg=BG_SURFACE, troughcolor=BG_ROOT,
                          activebackground=ACCENT_1)
        sb.pack(side="right", fill="y")

        self._log = tk.Text(
            frame,
            bg=BG_INPUT, fg=TEXT_PRIMARY,
            insertbackground=ACCENT_2,
            selectbackground=ACCENT_1, selectforeground=TEXT_PRIMARY,
            font=FONT_NORMAL,
            wrap="word",
            state="disabled",
            relief="flat", bd=0,
            padx=12, pady=10,
            yscrollcommand=sb.set,
        )
        self._log.pack(side="left", fill="both", expand=True)
        sb.config(command=self._log.yview)
        self._log.tag_config("ts", foreground=TEXT_MUTED, font=FONT_LABEL)

    # ------------------------------------------------------------------
    # Widget factories
    # ------------------------------------------------------------------

    def _btn(self, parent, text, bg, command):
        return tk.Button(
            parent, text=text, bg=bg, fg=TEXT_PRIMARY,
            activebackground=ACCENT_2, activeforeground=TEXT_PRIMARY,
            relief="flat", bd=0, padx=12, pady=6,
            font=FONT_SMALL, cursor="hand2", command=command,
        )

    def _toggle_btn(self, parent, text):
        return tk.Button(
            parent, text=text, bg=BG_SURFACE, fg=TEXT_SECONDARY,
            activebackground=ACCENT_1, activeforeground=TEXT_PRIMARY,
            relief="flat", bd=0, padx=10, pady=6,
            font=FONT_SMALL, cursor="hand2",
        )

    # ------------------------------------------------------------------
    # Public interface (called by YerrrpApp)
    # ------------------------------------------------------------------

    def set_status(self, msg: str):
        self._status_var.set(msg)

    def get_model(self) -> str:
        return self._model_var.get()

    def get_ptt(self) -> bool:
        return self._ptt_active

    def get_vibe(self) -> bool:
        return self._vibe_active

    def on_recording_started(self):
        self._rec_btn.config(text="■  Stop", bg=DANGER)
        self.set_status("Recording…")

    def on_recording_stopped(self):
        self._rec_btn.config(text="⏺  Record", bg=ACCENT_1)

    def append_entry(self, text: str):
        ts = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]  ")
        self._log.config(state="normal")
        if self._log.get("1.0", "end-1c").strip():
            self._log.insert("end", "\n\n")
        self._log.insert("end", ts, "ts")
        self._log.insert("end", text)
        self._log.see("end")
        self._log.config(state="disabled")
        self.set_status("Done")

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _toggle_record(self):
        if self.app.is_recording():
            self.app.stop_recording()
        else:
            self.app.start_recording()

    def _toggle_ptt(self):
        self._ptt_active = not self._ptt_active
        if self._ptt_active:
            self._ptt_btn.config(bg=ACCENT_1, fg=TEXT_PRIMARY)
        else:
            self._ptt_btn.config(bg=BG_SURFACE, fg=TEXT_SECONDARY)

    def _toggle_vibe(self):
        import os
        if not self._vibe_active:
            try:
                from openai import OpenAI  # noqa: F401
            except ImportError:
                messagebox.showwarning(
                    "Missing Package",
                    "Install the 'openai' package:\npip install openai",
                )
                return
            if not os.environ.get("XAI_API_KEY"):
                messagebox.showwarning(
                    "API Key Missing",
                    "Set XAI_API_KEY environment variable to use Vibe mode.",
                )
                return
        self._vibe_active = not self._vibe_active
        if self._vibe_active:
            self._vibe_btn.config(bg=ACCENT_2, fg=TEXT_PRIMARY)
        else:
            self._vibe_btn.config(bg=BG_SURFACE, fg=TEXT_SECONDARY)

    def _copy_all(self):
        text = self._log.get("1.0", "end-1c").strip()
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.set_status("Copied to clipboard")
        self.after(2000, lambda: self.set_status("Ready"))

    def _clear_log(self):
        self._log.config(state="normal")
        self._log.delete("1.0", "end")
        self._log.config(state="disabled")
        self.set_status("Ready")

    def _hide_to_tray(self):
        self.withdraw()
