# Yerrrp

A local speech-to-text desktop app — Bold & Vivid floating pill + system tray.

## Stack
- **UI**: tkinter (stdlib)
- **Transcription**: openai-whisper (local, no API key needed)
- **Vibe Code mode**: xAI Grok API via `openai` SDK (`XAI_API_KEY` env var required)
- **Audio**: sounddevice + numpy
- **Tray**: pystray + pillow
- **Global hotkey**: pynput
- **Auto-paste**: pyautogui (always fires after every transcription)

## Entry point
`python app.py` from `D:\dev\Yerrrp`

## File map
| File | Responsibility |
|---|---|
| `app.py` | `YerrrpApp` orchestrator, recording state machine, transcription |
| `main_window.py` | `MainWindow(tk.Tk)` — history log with timestamps, controls, Bold & Vivid theme |
| `pill_overlay.py` | `PillOverlay(tk.Toplevel)` — frameless pill, recording/transcribing/done states |
| `tray_icon.py` | `TrayIcon` — pystray daemon thread, programmatic purple mic icon |
| `hotkey_listener.py` | `HotkeyListener` — pynput Ctrl+Win hold/release PTT |
| `theme.py` | Colors, fonts, `round_rect()` canvas helper |
| `tests/test_hotkey.py` | Unit tests for HotkeyListener key-state logic |

## Architecture rules
- **Thread safety**: all tkinter calls from background threads MUST use `root.after(0, ...)`.
- **Close behavior**: closing `MainWindow` calls `withdraw()` — app stays alive in tray. Only tray "Quit" destroys the process.
- **PillOverlay** is a `Toplevel` child of `MainWindow`. Uses Windows `transparentcolor` trick: window bg = `#010203`, pill drawn on Canvas with `round_rect()`.
- **`<<PillStop>>`** virtual event fired by the pill's stop button, bound on `MainWindow` by `YerrrpApp`.
- **Auto-paste always fires** — `pynput.keyboard.Controller().type(text)` runs 200ms after every successful transcription. Uses Unicode `SendInput` (not Ctrl+V simulation) so it works in Electron apps, terminals, and native Win32 apps. Clipboard is also set as a manual fallback.
- **Pill never shows transcription text** — shows waveform during recording, "Transcribing…" spinner, then "✓ Done" for 1.5s. All text goes to the main window history log only.

## Hotkey
`Ctrl + Win` — hold to record, release to stop. Implemented via `pynput.keyboard.Listener` tracking both key states independently. Windows key maps to `Key.cmd` in pynput.

## Pill states
`hidden` → `recording` (waveform + timer, purple border) → `transcribing` ("Transcribing…") → `done` ("✓ Done", 1.5s) → `hidden`

## Dev notes
- Whisper models cached in `YerrrpApp._model_cache` after first load.
- `fp16=False` in `model.transcribe()` — required on CPU-only machines.
- Vibe mode requires `XAI_API_KEY` env var; uses `https://api.x.ai/v1` base URL with `grok-3-mini-fast` model.
- `round_rect()` in `theme.py` uses tkinter `create_polygon(..., smooth=True)` for pill shape.
