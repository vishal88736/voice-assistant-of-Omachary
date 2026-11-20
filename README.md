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

## Known limitations
- Wake word uses energy + transcription heuristic, not a trained openWakeWord model.
- Ollama model pull may take time.
- High-risk actions require confirmation (default deny in non-interactive).