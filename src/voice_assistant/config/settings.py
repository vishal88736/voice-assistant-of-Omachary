"""User configuration for the voice assistant."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


CONFIG_DIR = Path.home() / ".config" / "voice_assistant"
DATA_DIR = Path.home() / ".local" / "share" / "voice_assistant"
CACHE_DIR = Path.home() / ".cache" / "voice_assistant"
LOG_DIR = Path.home() / ".local" / "state" / "voice_assistant" / "logs"

for _d in (CONFIG_DIR, DATA_DIR, CACHE_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)


@dataclass
class Settings:
    assistant_name: str = "Nova"
    wake_word: str = "nova"
    wake_model: str = "placeholder"  # wake-word model; integrate your own later
    language_mode: str = "auto"  # auto | en | hi | hinglish
    tts_voice: str = "placeholder"
    tts_speed: float = 1.0
    stt_model: str = "placeholder"  # placeholder | tiny | base | small
    llm_model: str = "placeholder"  # placeholder until user selects a model
    llm_keep_alive_seconds: int = 90
    startup_greeting: bool = True
    wake_enabled: bool = False  # enable after a real wake-word/STT provider is integrated
    quiet_hours_start: int = 23
    quiet_hours_end: int = 7
    push_to_talk_key: str = "ctrl+space"
    microphone_device: str | None = None
    speaker_device: str | None = None
    memory_enabled: bool = False  # no long-term personal memory by default
    session_retention_days: int = 7
    max_sessions: int = 20
    privacy_mode: bool = True
    permissions: dict[str, str] = field(default_factory=lambda: {
        "low": "auto",
        "medium": "confirm",
        "high": "confirm",
    })
    projects: list[dict[str, Any]] = field(default_factory=list)
    known_facts: list[str] = field(default_factory=list)

    @classmethod
    def load(cls) -> "Settings":
        path = CONFIG_DIR / "settings.json"
        if not path.exists():
            s = cls()
            s.save()
            return s
        try:
            data = json.loads(path.read_text())
        except Exception:
            data = {}
        base = cls()
        for k, v in data.items():
            if hasattr(base, k):
                setattr(base, k, v)
        return base

    def save(self) -> None:
        path = CONFIG_DIR / "settings.json"
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False))


def db_path() -> Path:
    return DATA_DIR / "memory.db"


def log_path() -> Path:
    return LOG_DIR / "assistant.log"