# Yerrrp

A local speech-to-text desktop app built with tkinter + OpenAI Whisper.

## Stack
- **UI**: tkinter (stdlib)
- **Transcription**: openai-whisper (local, no API key needed)
- **Vibe Code mode**: xAI Grok API via `openai` SDK (`XAI_API_KEY` env var required)
- **Audio**: sounddevice + numpy
- **Auto-paste**: pyautogui

## Entry point
`app.py` — run with `python app.py`

## Features
- Record/Stop transcription
- Push-to-Talk (PTT) with auto-paste via pyautogui
- Vibe Code mode: formats raw transcription into a clean coding prompt via Grok
- Model selector (tiny → large)
- Copy/Clear text area

## Dev notes
- Whisper models are cached in `_model_cache` after first load to avoid reloading
- All UI updates from background threads go through `self.after(0, ...)` — never touch tkinter from a non-main thread
- PTT rebinds the Record button's mouse events; toggle off PTT to restore normal click behavior
- `XAI_API_KEY` env var must be set for Vibe Code mode; uses `https://api.x.ai/v1` base URL
