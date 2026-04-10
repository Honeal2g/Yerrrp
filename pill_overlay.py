"""Floating pill overlay — visible only during recording and result display."""
import math
import time
import tkinter as tk

from theme import (
    TRANSPARENT_KEY, PILL_HEIGHT, BG_CARD, ACCENT_1, ACCENT_2,
    DANGER, SUCCESS, TEXT_PRIMARY, TEXT_SECONDARY, round_rect,
)

# Waveform config
_BAR_COUNT = 7
_BAR_W     = 3
_BAR_GAP   = 2
_BAR_MIN_H = 4
_BAR_MAX_H = 20


class PillOverlay(tk.Toplevel):
    """Frameless, always-on-top pill widget. Call show_recording() / show_result() to activate."""

    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-transparentcolor", TRANSPARENT_KEY)
        self.config(bg=TRANSPARENT_KEY)
        self.withdraw()

        self._canvas = tk.Canvas(self, bg=TRANSPARENT_KEY, highlightthickness=0, bd=0)
        self._canvas.pack(fill="both", expand=True)

        # Drag state
        self._drag_ox = self._drag_oy = 0
        self._canvas.bind("<ButtonPress-1>", self._drag_start)
        self._canvas.bind("<B1-Motion>",     self._drag_move)

        # Default anchor: top-center of primary screen
        self._anchor_x = self.winfo_screenwidth() // 2
        self._anchor_y = 22

        self._state     = "hidden"
        self._wave_tick = 0
        self._wave_job  = self._hide_job = self._timer_job = None
        self._t_start   = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_recording(self):
        self._cancel_all()
        self._state   = "recording"
        self._t_start = time.monotonic()
        self._render_recording()
        self.deiconify()
        self._tick_wave()
        self._tick_timer()

    def show_transcribing(self):
        self._cancel_all()
        self._state = "transcribing"
        self._render_transcribing()

    def show_result(self, text: str):
        self._cancel_all()
        self._state = "done"
        self._render_done(text)
        self._hide_job = self.after(6000, self.hide)

    def hide(self):
        self._cancel_all()
        self._state = "hidden"
        self.withdraw()

    # ------------------------------------------------------------------
    # Drag
    # ------------------------------------------------------------------

    def _drag_start(self, event):
        self._drag_ox = event.x_root - self.winfo_x()
        self._drag_oy = event.y_root - self.winfo_y()

    def _drag_move(self, event):
        nx = event.x_root - self._drag_ox
        ny = event.y_root - self._drag_oy
        self._anchor_x = nx + self.winfo_width() // 2
        self._anchor_y = ny
        self.geometry(f"+{nx}+{ny}")

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    def _place(self, width: int):
        x = self._anchor_x - width // 2
        y = self._anchor_y
        self.geometry(f"{width}x{PILL_HEIGHT}+{x}+{y}")
        self._canvas.config(width=width, height=PILL_HEIGHT)

    def _pill(self, width: int, fill: str, border: str = None):
        h = PILL_HEIGHT
        r = (h - 8) // 2
        if border:
            round_rect(self._canvas, 1, 1, width - 1, h - 1, r + 3,
                       fill=border, outline=border, tags="pill_glow")
        round_rect(self._canvas, 4, 4, width - 4, h - 4, r,
                   fill=fill, outline=fill, tags="pill")

    # ------------------------------------------------------------------
    # Recording state
    # ------------------------------------------------------------------

    def _render_recording(self):
        w = 310
        self._place(w)
        c = self._canvas
        c.delete("all")
        self._pill(w, BG_CARD, border=ACCENT_2)

        # Stop button (red circle)
        cx, cy = 28, PILL_HEIGHT // 2
        c.create_oval(cx - 12, cy - 12, cx + 12, cy + 12,
                      fill=DANGER, outline="", tags="stop_btn")
        c.create_text(cx, cy, text="■", fill="white",
                      font=("Segoe UI", 8, "bold"), tags="stop_btn")
        c.tag_bind("stop_btn", "<Button-1>",
                   lambda _: self.master.event_generate("<<PillStop>>", when="tail"))

        self._wave_x = 50
        self._draw_bars()

        c.create_text(w - 32, PILL_HEIGHT // 2, text="0:00",
                      fill=TEXT_SECONDARY, font=("Segoe UI", 9), tags="timer")

    def _draw_bars(self):
        c = self._canvas
        c.delete("wave")
        x = self._wave_x
        cy = PILL_HEIGHT // 2
        for i in range(_BAR_COUNT):
            phase = (self._wave_tick + i * 4) % 24
            h = int(_BAR_MIN_H + (_BAR_MAX_H - _BAR_MIN_H) * abs(math.sin(phase * math.pi / 12)))
            c.create_rectangle(x, cy - h // 2, x + _BAR_W, cy + h // 2,
                                fill=ACCENT_2, outline="", tags="wave")
            x += _BAR_W + _BAR_GAP

    def _tick_wave(self):
        if self._state != "recording":
            return
        self._wave_tick += 1
        self._draw_bars()
        self._wave_job = self.after(80, self._tick_wave)

    def _tick_timer(self):
        if self._state != "recording":
            return
        elapsed = int(time.monotonic() - self._t_start)
        m, s = divmod(elapsed, 60)
        self._canvas.itemconfigure("timer", text=f"{m}:{s:02d}")
        self._timer_job = self.after(500, self._tick_timer)

    # ------------------------------------------------------------------
    # Transcribing state
    # ------------------------------------------------------------------

    def _render_transcribing(self):
        w = 210
        self._place(w)
        c = self._canvas
        c.delete("all")
        self._pill(w, BG_CARD, border=ACCENT_1)
        c.create_text(w // 2, PILL_HEIGHT // 2,
                      text="Transcribing…", fill=TEXT_SECONDARY,
                      font=("Segoe UI", 9, "italic"))

    # ------------------------------------------------------------------
    # Done state
    # ------------------------------------------------------------------

    def _render_done(self, text: str):
        display = text if len(text) <= 46 else text[:43] + "…"
        tw = int(len(display) * 6.5)
        copy_w = 52
        w = max(min(tw + copy_w + 48, 520), 200)

        self._place(w)
        c = self._canvas
        c.delete("all")
        self._pill(w, BG_CARD, border=SUCCESS)

        text_x = (w - copy_w - 16) // 2 + 8
        c.create_text(text_x, PILL_HEIGHT // 2, text=display,
                      fill=TEXT_PRIMARY, font=("Segoe UI", 9), anchor="center")

        bx1, bx2 = w - copy_w - 6, w - 6
        by1, by2 = 9, PILL_HEIGHT - 9
        round_rect(c, bx1, by1, bx2, by2, 6,
                   fill=ACCENT_1, outline=ACCENT_1, tags="copy_btn")
        c.create_text((bx1 + bx2) // 2, (by1 + by2) // 2, text="Copy",
                      fill="white", font=("Segoe UI", 8, "bold"), tags="copy_btn")
        c.tag_bind("copy_btn", "<Button-1>", lambda _: self._do_copy(text))

    def _do_copy(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.hide()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _cancel_all(self):
        for attr in ("_wave_job", "_hide_job", "_timer_job"):
            job = getattr(self, attr)
            if job:
                self.after_cancel(job)
            setattr(self, attr, None)
