"""Yerrrp — Speech-to-Text Desktop App

A tkinter application that records audio from the microphone and transcribes
it using OpenAI Whisper (local). Supports standard record/stop, push-to-talk
with auto-paste, and a Vibe Code mode that formats transcriptions into clean
coding prompts via the Grok (xAI) API.
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import numpy as np
    import sounddevice as sd
    import whisper

    _DEPS_AVAILABLE = True
    _DEPS_ERROR = ""
except ImportError as e:
    _DEPS_AVAILABLE = False
    _DEPS_ERROR = str(e)

try:
    import pyautogui

    _PYAUTOGUI_AVAILABLE = True
except ImportError:
    _PYAUTOGUI_AVAILABLE = False

try:
    from openai import OpenAI

    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]
DEFAULT_MODEL = "base"
SAMPLE_RATE = 16000

VIBE_SYSTEM_PROMPT = (
    "You are a prompt formatter for AI coding tools. Take the user's spoken "
    "transcription and rewrite it as a clean, well-structured coding prompt. "
    "Fix filler words, hesitations, and grammar. Keep the user's intent exactly. "
    "Output only the formatted prompt, nothing else."
)


class SpeechToTextApp(tk.Tk):
    def __init__(self):
        super().__init__()

        if not _DEPS_AVAILABLE:
            self.withdraw()
            messagebox.showerror(
                "Missing Dependencies",
                f"Required packages are missing:\n{_DEPS_ERROR}\n\n"
                "Install with:\n"
                "pip install openai-whisper sounddevice numpy",
            )
            self.destroy()
            return

        self.title("Yerrrp")
        self.geometry("650x450")
        self.minsize(450, 300)

        self._recording = False
        self._ptt_mode = False
        self._vibe_mode = False
        self._audio_frames = []
        self._model_cache = {}
        self._stream = None

        self._build_ui()

    def _build_ui(self):
        # --- Toolbar ---
        toolbar = ttk.Frame(self)
        toolbar.pack(side="top", fill="x", padx=6, pady=(6, 2))

        ttk.Label(toolbar, text="Model:").pack(side="left", padx=(0, 4))
        self._model_var = tk.StringVar(value=DEFAULT_MODEL)
        self._model_combo = ttk.Combobox(
            toolbar,
            textvariable=self._model_var,
            values=WHISPER_MODELS,
            state="readonly",
            width=8,
        )
        self._model_combo.pack(side="left", padx=(0, 8))

        self._record_btn = tk.Button(
            toolbar,
            text="Record",
            width=10,
            bg="#4CAF50",
            fg="white",
            command=self._toggle_record,
        )
        self._record_btn.pack(side="left", padx=4)

        self._ptt_btn = tk.Button(
            toolbar,
            text="PTT",
            width=6,
            relief="raised",
            command=self._toggle_ptt,
        )
        self._ptt_btn.pack(side="left", padx=4)

        self._vibe_btn = tk.Button(
            toolbar,
            text="Vibe",
            width=6,
            relief="raised",
            command=self._toggle_vibe,
        )
        self._vibe_btn.pack(side="left", padx=4)

        self._copy_btn = tk.Button(
            toolbar,
            text="Copy",
            width=6,
            command=self._copy_to_clipboard,
        )
        self._copy_btn.pack(side="left", padx=4)

        self._clear_btn = tk.Button(
            toolbar,
            text="Clear",
            width=6,
            command=self._clear_text,
        )
        self._clear_btn.pack(side="left", padx=4)

        # --- Status bar ---
        self._status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            self, textvariable=self._status_var, relief="sunken", anchor="w"
        )
        status_bar.pack(side="top", fill="x", padx=6, pady=2)

        # --- Text area ---
        text_frame = ttk.Frame(self)
        text_frame.pack(side="top", fill="both", expand=True, padx=6, pady=(2, 6))

        self._scrollbar = ttk.Scrollbar(text_frame)
        self._scrollbar.pack(side="right", fill="y")

        self._text_area = tk.Text(
            text_frame,
            wrap="word",
            state="disabled",
            yscrollcommand=self._scrollbar.set,
            font=("TkDefaultFont", 11),
        )
        self._text_area.pack(side="left", fill="both", expand=True)
        self._scrollbar.config(command=self._text_area.yview)

    # --- Recording modes ---

    def _toggle_ptt(self):
        self._ptt_mode = not self._ptt_mode
        if self._ptt_mode:
            self._ptt_btn.config(relief="sunken", bg="#2196F3", fg="white")
            self._record_btn.unbind("<Button-1>")
            self._record_btn.config(command="")  # disable normal click
            self._record_btn.bind("<ButtonPress-1>", self._ptt_press)
            self._record_btn.bind("<ButtonRelease-1>", self._ptt_release)
            self._set_status("PTT mode ON — hold Record to speak")
        else:
            self._ptt_btn.config(relief="raised", bg="SystemButtonFace", fg="black")
            self._record_btn.unbind("<ButtonPress-1>")
            self._record_btn.unbind("<ButtonRelease-1>")
            self._record_btn.config(command=self._toggle_record)
            self._set_status("Ready")

    def _ptt_press(self, event=None):
        if not self._recording:
            self._start_recording()

    def _ptt_release(self, event=None):
        if self._recording:
            self._stop_recording()

    def _toggle_vibe(self):
        if not _OPENAI_AVAILABLE:
            messagebox.showwarning(
                "Missing Dependency",
                "The 'openai' package is not installed.\n\n"
                "Install with: pip install openai",
            )
            return

        if not os.environ.get("XAI_API_KEY"):
            messagebox.showwarning(
                "API Key Missing",
                "XAI_API_KEY environment variable is not set.\n\n"
                "Vibe Code mode requires a valid xAI API key to format prompts.",
            )
            return

        self._vibe_mode = not self._vibe_mode
        if self._vibe_mode:
            self._vibe_btn.config(relief="sunken", bg="#9C27B0", fg="white")
            self._set_status("Vibe Code mode ON")
        else:
            self._vibe_btn.config(relief="raised", bg="SystemButtonFace", fg="black")
            self._set_status("Ready")

    def _toggle_record(self):
        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        self._audio_frames = []
        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                callback=self._audio_callback,
            )
            self._stream.start()
        except Exception as e:
            messagebox.showerror(
                "Recording Error",
                f"Could not open microphone:\n{e}\n\n"
                "Check that a microphone is connected and permissions are granted.",
            )
            return

        self._recording = True
        self._record_btn.config(text="Stop", bg="#f44336")
        self._set_status("Recording...")

    def _audio_callback(self, indata, frames, time, status):
        self._audio_frames.append(indata.copy())

    def _stop_recording(self):
        self._recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        self._record_btn.config(text="Record", bg="#4CAF50")

        if not self._audio_frames:
            self._set_status("Recording too short")
            return

        audio_data = np.concatenate(self._audio_frames, axis=0).flatten()
        if len(audio_data) < SAMPLE_RATE * 0.1:  # less than 0.1 seconds
            self._set_status("Recording too short")
            return

        self._start_transcription(audio_data)

    # --- Transcription ---

    def _start_transcription(self, audio_data):
        self._record_btn.config(state="disabled")
        self._set_status("Transcribing...")
        thread = threading.Thread(
            target=self._run_transcription, args=(audio_data,), daemon=True
        )
        thread.start()

    def _run_transcription(self, audio_data):
        try:
            model_name = self._model_var.get()
            if model_name not in self._model_cache:
                self.after(0, self._set_status, f"Loading '{model_name}' model...")
                self._model_cache[model_name] = whisper.load_model(model_name)
            model = self._model_cache[model_name]

            self.after(0, self._set_status, "Transcribing...")
            result = model.transcribe(audio_data, fp16=False)
            text = result["text"].strip()

            if not text:
                self.after(0, self._transcription_done, "(no speech detected)")
                return

            if self._vibe_mode:
                self.after(0, self._set_status, "Formatting prompt...")
                text = self._format_prompt(text)

            self.after(0, self._transcription_done, text)
        except Exception as e:
            self.after(0, self._transcription_error, str(e))

    def _format_prompt(self, raw_text):
        try:
            client = OpenAI(
                api_key=os.environ.get("XAI_API_KEY"),
                base_url="https://api.x.ai/v1",
            )
            response = client.chat.completions.create(
                model="grok-3-mini-fast",
                max_tokens=1024,
                messages=[
                    {"role": "system", "content": VIBE_SYSTEM_PROMPT},
                    {"role": "user", "content": raw_text},
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return raw_text  # fall back to raw transcription

    def _transcription_done(self, text):
        self._record_btn.config(state="normal")
        self._append_text(text)
        self._set_status("Done")

        if self._ptt_mode:
            self._auto_paste(text)

    def _transcription_error(self, error_msg):
        self._record_btn.config(state="normal")
        self._set_status("Error")
        messagebox.showerror("Transcription Error", error_msg)

    # --- Auto-paste (PTT mode) ---

    def _auto_paste(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        if _PYAUTOGUI_AVAILABLE:
            self.after(100, self._simulate_paste)
        else:
            self._set_status("Done — copied to clipboard (install pyautogui for auto-paste)")

    def _simulate_paste(self):
        try:
            pyautogui.hotkey("ctrl", "v")
        except Exception:
            pass  # best-effort; clipboard still has the text

    # --- Clipboard / text area ---

    def _copy_to_clipboard(self):
        text = self._text_area.get("1.0", "end-1c")
        if not text.strip():
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self._set_status("Copied to clipboard")
        self.after(2000, lambda: self._set_status("Ready"))

    def _clear_text(self):
        self._text_area.config(state="normal")
        self._text_area.delete("1.0", "end")
        self._text_area.config(state="disabled")
        self._set_status("Ready")

    def _append_text(self, text):
        self._text_area.config(state="normal")
        if self._text_area.get("1.0", "end-1c").strip():
            self._text_area.insert("end", "\n\n")
        self._text_area.insert("end", text)
        self._text_area.see("end")
        self._text_area.config(state="disabled")

    def _set_status(self, msg):
        self._status_var.set(msg)


if __name__ == "__main__":
    app = SpeechToTextApp()
    app.mainloop()
