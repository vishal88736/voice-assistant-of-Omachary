"""Application entrypoint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from voice_assistant.config.settings import Settings
from voice_assistant.core.assistant import Assistant
from voice_assistant.config.logger import get_logger

log = get_logger()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode")
    args = parser.parse_args()

    import fcntl
    import os
    lock_path = Path.home() / ".cache" / "voice_assistant" / "app.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = open(lock_path, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("Voice Assistant already running.")
        sys.exit(0)

    settings = Settings.load()
    assistant = Assistant(settings=settings)

    # Ensure Ollama is running
    from voice_assistant.llm.ollama import OllamaClient
    oc = OllamaClient()
    if not oc.is_available():
        import subprocess
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import time
        for _ in range(20):
            time.sleep(1)
            if oc.is_available():
                break

    if args.cli:
        assistant.on_state = lambda state, text: None
        assistant.start()
        print(f"{settings.assistant_name} ready. Type 'quit' to exit.")
        try:
            while True:
                line = input("> ").strip()
                if line.lower() in ("quit", "exit"):
                    break
                print(assistant.process_text(line))
        finally:
            assistant.stop()
        return

    from PySide6.QtWidgets import QApplication
    from voice_assistant.ui.window import AssistantWindow

    app = QApplication(sys.argv)
    window = AssistantWindow(assistant)
    assistant.on_state = window.update_state
    assistant.start()
    window.show()
    ret = app.exec()
    assistant.stop()
    sys.exit(ret)


if __name__ == "__main__":
    main()