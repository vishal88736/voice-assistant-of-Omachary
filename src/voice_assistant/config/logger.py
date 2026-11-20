"""Logging setup."""

from __future__ import annotations

import logging
from pathlib import Path

from .settings import log_path


def get_logger(name: str = "voice_assistant") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        fh = logging.FileHandler(log_path())
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        pass
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger