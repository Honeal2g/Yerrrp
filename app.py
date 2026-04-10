"""Yerrrp — Speech-to-Text Desktop App.

Entry point and orchestrator. Owns all recording state and wires the four
components (MainWindow, PillOverlay, TrayIcon, HotkeyListener) together.
"""
import os
import threading

try:
    import numpy as np
    import sounddevice as sd
    import whisper
    _DEPS_OK  = True
    _DEPS_ERR = ""
except ImportError as e:
    _DEPS_OK  = False
    _DEPS_ERR = str(e)

try:
    import pyautogui
    _PYAUTOGUI_OK = True
except ImportError:
    _PYAUTOGUI_OK = False

try:
    from openai import OpenAI
    _OPENAI_OK = True
except ImportError:
    _OPENAI_OK = False

SAMPLE_RATE = 16000

VIBE_SYSTEM_PROMPT = (
    "You are a prompt formatter for AI coding tools. Take the user's spoken "
    "transcription and rewrite it as a clean, well-structured coding prompt. "
    "Fix filler words, hesitations, and grammar. Keep the user's intent exactly. "
    "Output only the formatted prompt, nothing else."
)


class YerrrpApp:
    """Orchestrates all Yerrrp components. Call .run() to start the event loop."""

    def __init__(self):
        from main_window import MainWindow
        from pill_overlay import PillOverlay
        from tray_icon import TrayIcon
        from hotkey_listener import HotkeyListener

        self._recording    = False
        self._audio_frames = []
        self._stream       = None
        self._model_cache  = {}

        # MainWindow IS the tk.Tk root
        self.main = MainWindow(self)
        self.pill = PillOverlay(self.main)

        self.tray = TrayIcon(
            on_show=lambda: self.main.after(0, self._show_main),
            on_quit=lambda: self.main.after(0, self._quit),
        )
        self.hotkey = HotkeyListener(
            on_press_cb=lambda: self.main.after(0, self.start_recording),
            on_release_cb=lambda: self.main.after(0, self.stop_recording),
        )

        # Pill stop button fires this virtual event on the root window
        self.main.bind("<<PillStop>>", lambda _: self.stop_recording())

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def run(self):
        if not _DEPS_OK:
            from tkinter import messagebox
            self.main.withdraw()
            messagebox.showerror(
                "Missing Dependencies",
                f"Required packages are missing:\n{_DEPS_ERR}\n\n"
                "Install with:\n"
                "pip install openai-whisper sounddevice numpy",
            )
            return
        self.tray.start()
        self.hotkey.start()
        self.main.mainloop()

    def _show_main(self):
        self.main.deiconify()
        self.main.lift()
        self.main.focus_force()

    def _quit(self):
        self.tray.stop()
        self.hotkey.stop()
        self.main.quit()
        self.main.destroy()

    # ------------------------------------------------------------------
    # Recording state
    # ------------------------------------------------------------------

    def is_recording(self) -> bool:
        return self._recording

    def start_recording(self):
        if self._recording:
            return
        self._audio_frames = []
        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                callback=self._audio_cb,
            )
            self._stream.start()
        except Exception as e:
            self.main.set_status(f"Mic error: {e}")
            return

        self._recording = True
        self.main.on_recording_started()
        self.pill.show_recording()

    def _audio_cb(self, indata, frames, time, status):
        self._audio_frames.append(indata.copy())

    def stop_recording(self):
        if not self._recording:
            return
        self._recording = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        self.main.on_recording_stopped()

        if not self._audio_frames:
            self.pill.hide()
            return

        audio = np.concatenate(self._audio_frames, axis=0).flatten()
        if len(audio) < SAMPLE_RATE * 0.1:
            self.pill.hide()
            self.main.set_status("Recording too short")
            return

        self.pill.show_transcribing()
        self.main.set_status("Transcribing…")
        threading.Thread(target=self._transcribe, args=(audio,), daemon=True).start()

    # ------------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------------

    def _transcribe(self, audio):
        try:
            model_name = self.main.get_model()
            if model_name not in self._model_cache:
                self.main.after(0, self.main.set_status, f"Loading '{model_name}' model…")
                self._model_cache[model_name] = whisper.load_model(model_name)
            model = self._model_cache[model_name]

            result = model.transcribe(audio, fp16=False)
            text = result["text"].strip() or "(no speech detected)"

            if self.main.get_vibe() and text != "(no speech detected)":
                self.main.after(0, self.main.set_status, "Formatting prompt…")
                text = self._vibe_format(text)

            self.main.after(0, self._on_transcribed, text)
        except Exception as e:
            self.main.after(0, self._on_error, str(e))

    def _on_transcribed(self, text: str):
        self.main.append_entry(text)
        self.pill.show_result(text)
        if self.main.get_ptt():
            self._auto_paste(text)

    def _on_error(self, msg: str):
        self.pill.hide()
        self.main.set_status(f"Error: {msg}")

    def _vibe_format(self, raw: str) -> str:
        if not _OPENAI_OK:
            return raw
        try:
            client = OpenAI(
                api_key=os.environ.get("XAI_API_KEY"),
                base_url="https://api.x.ai/v1",
            )
            resp = client.chat.completions.create(
                model="grok-3-mini-fast",
                max_tokens=1024,
                messages=[
                    {"role": "system", "content": VIBE_SYSTEM_PROMPT},
                    {"role": "user",   "content": raw},
                ],
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            return raw

    def _auto_paste(self, text: str):
        self.main.clipboard_clear()
        self.main.clipboard_append(text)
        if _PYAUTOGUI_OK:
            self.main.after(120, lambda: pyautogui.hotkey("ctrl", "v"))


if __name__ == "__main__":
    YerrrpApp().run()
