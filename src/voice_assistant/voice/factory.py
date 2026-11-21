"""Select voice providers based on settings.

Default settings use placeholders. To integrate a real voice model, set
`tts_voice` / `stt_model` to a non-placeholder value and implement the
corresponding provider here or in voice/base.py.
"""

from __future__ import annotations

from pathlib import Path

from ..config.settings import Settings
from .base import PlaceholderSTT, PlaceholderTTS
from .stt import transcribe_file
from .tts import PiperTTS


class VoxtypeSTT:
    def transcribe(self, path: Path) -> str:
        return transcribe_file(path)


def get_tts(settings: Settings):
    if not settings.tts_voice or settings.tts_voice == "placeholder":
        return PlaceholderTTS()
    return PiperTTS(settings.tts_voice)


def get_stt(settings: Settings):
    if not settings.stt_model or settings.stt_model == "placeholder":
        return PlaceholderSTT()
    return VoxtypeSTT()