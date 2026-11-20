"""Audio capture and WAV writing."""

from __future__ import annotations

import wave
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd


class AudioRecorder:
    def __init__(self, sample_rate: int = 16000, channels: int = 1, device: Optional[int] = None):
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device
        self._frames: list[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None

    def start(self) -> None:
        self._frames = []
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            device=self.device,
            dtype="int16",
            callback=self._cb,
        )
        self._stream.start()

    def _cb(self, indata, frames, time_info, status):
        self._frames.append(indata.copy())

    def stop(self) -> np.ndarray:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._frames:
            return np.zeros(0, dtype=np.int16)
        return np.concatenate(self._frames, axis=0).reshape(-1)

    def save_wav(self, path: Path, data: Optional[np.ndarray] = None) -> Path:
        if data is None:
            data = self.stop()
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(data.astype(np.int16).tobytes())
        return path