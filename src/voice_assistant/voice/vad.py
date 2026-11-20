"""Voice activity detection helpers (energy-based, no webrtcvad)."""

from __future__ import annotations

import numpy as np


def contains_speech(pcm_bytes: bytes, sample_rate: int = 16000, frame_ms: int = 30) -> bool:
    if not pcm_bytes:
        return False
    data = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
    if data.size == 0:
        return False
    rms = np.sqrt(np.mean(data ** 2))
    return rms > 300.0