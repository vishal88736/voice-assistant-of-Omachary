"""Hyprland and system control helpers."""

from __future__ import annotations

import json
import subprocess
from typing import Any


def run(cmd: list[str], timeout: int = 10) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except Exception as e:
        return 1, "", str(e)


def hyprctl(args: list[str]) -> tuple[int, str]:
    rc, out, err = run(["hyprctl"] + args)
    return rc, out if rc == 0 else err


def active_window() -> dict[str, Any]:
    rc, out = hyprctl(["activewindow", "-j"])
    try:
        return json.loads(out)
    except Exception:
        return {}


def list_windows() -> list[dict[str, Any]]:
    rc, out = hyprctl(["clients", "-j"])
    try:
        return json.loads(out)
    except Exception:
        return []


def focus_window(address: str) -> bool:
    rc, _ = hyprctl(["dispatch", "focuswindow", f"address:{address}"])
    return rc == 0


def switch_workspace(ws: str) -> bool:
    rc, _ = hyprctl(["dispatch", "workspace", str(ws)])
    return rc == 0


def toggle_fullscreen() -> bool:
    rc, _ = hyprctl(["dispatch", "fullscreen", "0"])
    return rc == 0


def move_window_to_workspace(address: str, ws: str) -> bool:
    rc, _ = hyprctl(["dispatch", "movetoworkspace", f"{ws},address:{address}"])
    return rc == 0


def set_volume(delta: str) -> bool:
    # delta like "+5%" or "-5%" or "50%"
    rc, _, _ = run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", delta])
    return rc == 0


def get_volume() -> str:
    rc, out, _ = run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
    return out.strip()


def set_brightness(delta: str) -> bool:
    rc, _, _ = run(["brightnessctl", "set", delta])
    return rc == 0


def launch_app(name: str) -> bool:
    # Use omarchy-launch? Try hyprctl dispatch exec
    rc, _ = hyprctl(["dispatch", "exec", name])
    if rc != 0:
        # fallback
        subprocess.Popen(name, shell=True)
    return True


def close_app(address: str) -> bool:
    rc, _ = hyprctl(["dispatch", "closewindow", f"address:{address}"])
    return rc == 0


def battery_info() -> str:
    rc, out, _ = run(["omarchy-battery-status", "--shell"], timeout=5)
    if rc != 0:
        # fallback upower
        rc2, out2, _ = run(["upower", "-i", "/org/freedesktop/UPower/devices/battery_BAT0"])
        return out2.strip() or "Battery info unavailable"
    return out.strip()


def cpu_ram_info() -> str:
    rc, out, _ = run(["free", "-h"])
    return out.strip()


def disk_info() -> str:
    rc, out, _ = run(["df", "-h", "/"])
    return out.strip()