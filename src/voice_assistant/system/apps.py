"""Application launching helpers."""

from __future__ import annotations

import subprocess
from typing import Optional

APP_ALIASES = {
    "chrome": "google-chrome-stable",
    "chromium": "chromium",
    "vs code": "code",
    "vscode": "code",
    "code": "code",
    "terminal": "ghostty",
    "ghostty": "ghostty",
    "alacritty": "alacritty",
    "kitty": "kitty",
    "files": "nautilus",
    "file manager": "nautilus",
    "nautilus": "nautilus",
    "spotify": "spotify",
    "firefox": "firefox",
    "brave": "brave",
}


def resolve_app(name: str) -> Optional[str]:
    key = name.strip().lower()
    return APP_ALIASES.get(key, key)


def open_app(name: str) -> bool:
    cmd = resolve_app(name)
    if not cmd:
        return False
    try:
        subprocess.Popen([cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        # try shell
        try:
            subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False