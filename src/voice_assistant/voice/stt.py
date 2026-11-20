"""Speech-to-text via voxtype (offline whisper)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ..config.logger import get_logger

log = get_logger()


def transcribe_file(path: Path) -> str:
    import shutil
    if shutil.which("voxtype") is None:
        return ""
    try:
        p = subprocess.run(
            ["voxtype", "transcribe", str(path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        out = p.stdout.strip()
        if p.returncode != 0:
            log.warning("voxtype transcribe failed: %s", p.stderr)
        return out
    except Exception as e:
        log.error("STT error: %s", e)
        return ""


def record_and_transcribe(recorder, seconds: float = 4.0) -> str:
    import time
    recorder.start()
    time.sleep(seconds)
    data = recorder.stop()
    tmp = Path("/tmp/opencode") / "stt.wav"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    recorder.save_wav(tmp, data)
    return transcribe_file(tmp)