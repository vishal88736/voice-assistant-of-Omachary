# Troubleshooting

## Ollama not running
Run `ollama serve` or enable service: `systemctl --user enable --now ollama.service`.

## Model missing
`ollama pull qwen2.5:7b`

## Piper TTS fails
Ensure LD_LIBRARY_PATH includes ~/.local/share/piper.

## Microphone not detected
Check `pactl list short sources`. Set microphone in settings.

## Wake word false positives
Increase VAD threshold or use push-to-talk.

## Permission denied for medium/high actions
Approve in dialog/CLI prompt.