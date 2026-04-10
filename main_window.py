"""Yerrrp main window — Bold & Vivid redesign."""
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

from theme import (
    BG_ROOT, BG_CARD, BG_SURFACE, BG_INPUT, ACCENT_1, ACCENT_2, ACCENT_BORDER,
    DANGER, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_BOLD, FONT_NORMAL, FONT_SMALL, FONT_LABEL,
)

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
