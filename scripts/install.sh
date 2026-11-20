#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/.venv"
PYTHON="$VENV/bin/python"

echo "Creating venv if needed..."
if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -r "$ROOT/requirements.txt"

echo "Ensuring Ollama..."
if ! command -v ollama >/dev/null 2>&1 && [ ! -x "$HOME/.local/ollama/bin/ollama" ]; then
  echo "Please install Ollama manually (see docs)."
fi

echo "Installing desktop entry..."
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/voice-assistant.desktop <<EOF
[Desktop Entry]
Type=Application
Name=Voice Assistant
Exec=$ROOT/.venv/bin/python $ROOT/src/voice_assistant/app/main.py
Icon=audio-input-microphone
Terminal=false
Categories=Utility;
EOF

echo "Done."