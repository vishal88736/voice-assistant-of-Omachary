"""Voice provider interfaces and placeholders.

The actual voice model is intentionally left as a placeholder. Integrate a
provider by implementing TTSProvider / STTProvider and selecting it in
voice.factory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..config.logger import get_logger

log = get_logger()


class TTSProvider(Protocol):
    def speak(self, text: str) -> None: ...
    def stop(self) -> None: ...


class STTProvider(Protocol):
    def transcribe(self, path: Path) -> str: ...


class PlaceholderTTS:
    """No-op TTS used until a voice model is integrated."""

    def speak(self, text: str) -> None:
        log.info("TTS placeholder: %s", text)

    def stop(self) -> None:
        pass


class PlaceholderSTT:
    """No-op STT used until a voice model is integrated."""

    def transcribe(self, path: Path) -> str:
        log.info("STT placeholder: %s", path)
        return ""