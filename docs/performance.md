# Performance and Battery Optimization

The assistant is designed to keep heavy models off the CPU/GPU while idle.

## Model lifecycle
- The LLM is loaded only for conversational requests.
- Deterministic commands (open app, volume, workspace, system info, files) never load the LLM.
- A single idle timer unloads the model after `llm_keep_alive_seconds` (90s on AC, 20s on battery).
- `keep_alive` and `num_ctx` are passed to Ollama; the unload is verified via `/api/ps`.
- `stop()` unloads both the primary and battery models.

## Battery-aware policy
- `battery_aware = true` detects AC vs battery from `/sys/class/power_supply`.
- On battery, `llm_model_battery` is used when configured, and the idle timeout is shorter.
- Low-memory guard falls back to command mode below 1 GB free.

## Recommended model choices
- On AC: 7B Q4_K_M (e.g. Qwen2.5 7B) fits ~6 GB VRAM.
- On battery: 3B Q4_K_M or a smaller model; set `llm_model_battery`.
- Use `num_ctx` 2048–4096 to limit KV-cache memory.

## Ollama environment
Recommended in the Ollama user service:
```
Environment=OLLAMA_MAX_LOADED_MODELS=1
Environment=OLLAMA_NUM_PARALLEL=1
Environment=OLLAMA_KEEP_ALIVE=0
Environment=OLLAMA_FLASH_ATTENTION=1
```
`OLLAMA_KEEP_ALIVE=0` is a safety net; the app already passes explicit `keep_alive`.

## Voice pipeline
- Wake model is a placeholder and disabled by default.
- Prefer a lightweight ONNX wake-word detector (openWakeWord-style) over continuous Whisper.
- Use VAD before STT; transcribe only detected speech.
- Use Whisper tiny/base with whisper.cpp; avoid loading the model at idle.
- Piper TTS is spawned per utterance, so no TTS model stays resident.

## UI
- The Qt UI loads no WebEngine.
- No animations or continuous polling.
- Idle RSS measured ~114 MB; idle CPU ~0.5%; GPU 2 MiB.

## Measured example (qwen2.5:7b, RTX 4050)
- Cold start: 6.0 s
- Loaded GPU memory: 4,648 MiB
- After unload: 2 MiB, `ollama ps` empty
- Benchmark: `PYTHONPATH=src .venv/bin/python scripts/benchmark.py --model qwen2.5:7b`