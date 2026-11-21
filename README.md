# Voice Assistant for Omarchy Linux

A local-first personal AI companion for Omarchy Linux (Hyprland/Wayland).

## Features
- Text and voice conversation
- Offline STT (voxtype) and TTS (Piper)
- Persistent memory (SQLite)
- Deterministic command handling (no LLM for simple commands)
- On-demand LLM via Ollama (Qwen 2.5 7B)
- Desktop automation (Hyprland, apps, volume, files, git)
- Permission system
- Auto-start on login

## Install
```bash
cd "/home/vishal/D DRIVE/VOICE ASSISTANCE"
bash scripts/install.sh
```

## Run
```bash
voice-assistant          # GUI
voice-assistant --cli    # CLI
```

## Services
```bash
systemctl --user enable --now ollama.service
systemctl --user enable --now voice-assistant.service
```

## Models
Ollama model: qwen2.5:7b (pulled automatically or run `ollama pull qwen2.5:7b`).

## Voice models
Piper voices stored in ~/.local/share/voice_assistant/voices.

## Privacy and sessions
- Conversation history is kept per session in SQLite.
- Old sessions are auto-deleted after `session_retention_days` (default 7) and at most `max_sessions` (default 20) are kept.
- `privacy_mode` clears long-term personal memories on startup; only session history remains.
- File edits, deletes, moves, and other high-risk actions require explicit confirmation.
- No personal profile is injected into the model.

## Battery and performance
- LLM loads only for conversation and unloads after idle (90s AC / 20s battery).
- Deterministic commands never load the LLM.
- On battery, a smaller `llm_model_battery` can be used automatically.
- Wake detection is disabled until a wake model is integrated.
- See [docs/performance.md](docs/performance.md) for tuning and measured numbers.

## Placeholders
- `llm_model = "placeholder"` — select your model when ready.
- `tts_voice = "placeholder"` and `stt_model = "placeholder"` — integrate your voice model when ready.
- `wake_model = "placeholder"` — integrate your wake-word model when ready.

## Known limitations
- Wake word is not active until a wake model is integrated.
- High-risk actions require confirmation (default deny in non-interactive).