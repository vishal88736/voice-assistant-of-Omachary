"""Text-to-speech via Piper."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from ..config.logger import get_logger
from ..config.settings import DATA_DIR

log = get_logger()

PIPER_DIR = Path.home() / ".local" / "share" / "piper"
VOICES_DIR = Path.home() / ".local" / "share" / "voice_assistant" / "voices"


class PiperTTS:
    def __init__(self, voice: str = "en_US-lessac-medium"):
        self.voice = voice
        self._proc: subprocess.Popen | None = None
        os.environ.setdefault("LD_LIBRARY_PATH", str(PIPER_DIR))

    def _model_path(self) -> Path:
        return VOICES_DIR / f"{self.voice}.onnx"

    def speak(self, text: str) -> None:
        self.stop()
        if self.voice == "placeholder":
            log.info("TTS placeholder: %s", text)
            return
        model = self._model_path()
        if not model.exists():
            log.warning("TTS voice model missing: %s", model)
            return
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav = Path(f.name)
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = str(PIPER_DIR) + ":" + env.get("LD_LIBRARY_PATH", "")
        try:
            p = subprocess.run(
                [str(PIPER_DIR / "piper"), "--model", str(model), "--output_file", str(wav)],
                input=text,
                capture_output=True,
                text=True,
                env=env,
                timeout=60,
            )
            if p.returncode != 0:
                log.error("piper failed: %s", p.stderr)
                return
            # play
            self._proc = subprocess.Popen(["aplay", "-q", str(wav)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._proc.wait()
        except Exception as e:
            log.error("TTS error: %s", e)
        finally:
            try:
                wav.unlink(missing_ok=True)
            except Exception:
                pass

    def stop(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            try:
                self._proc.terminate()
            except Exception:
                pass
        self._proc = None