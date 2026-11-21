# Implementation Report

## Completed
- Project structure and modular architecture.
- Configuration and logging.
- SQLite persistent memory with FTS search.
- Permission manager with risk levels.
- Tool registry and system tools (apps, volume, brightness, workspaces, files, git, tests).
- Deterministic intent classifier for EN/HI/Hinglish commands.
- PySide6 GUI and CLI entrypoint.
- Startup integration (systemd user services, Hyprland autostart, desktop entry).
- Audit logging.

## UI and sessions
- Compact dark UI with session sidebar, chat history, new/delete/forget controls.
- Per-session conversation history in SQLite.
- Auto-retention deletes old sessions; privacy mode clears long-term memories.
- File edits/deletes/moves require explicit confirmation.

## Placeholders
- LLM model: `placeholder` (user to select).
- Voice STT/TTS: `placeholder` (user to integrate).
- Wake model: `placeholder` (user to integrate).

## Tests
- pytest: 7 passed (intent, memory, tools).

## Measured idle (with placeholders, no wake loop)
- CPU: ~0.5%
- RSS: ~114 MB
- GPU: 0 MiB (no model loaded)

## Model lifecycle
- Single idle unload timer (90s AC / 20s battery).
- Battery-aware model selection.
- Low-memory fallback to command mode.
- `num_ctx` and `keep_alive` passed to Ollama.
- Measured qwen2.5:7b: 6.0s cold start, 4,648 MiB VRAM loaded, 2 MiB after unload.

## Known limitations
- Wake word is heuristic (energy + transcription), not trained.
- High-risk actions default deny unless confirmed.
- No browser automation beyond URL opening (not implemented).