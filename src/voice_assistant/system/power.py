"""Power and resource awareness."""

from __future__ import annotations

from pathlib import Path

import psutil


def on_ac_power() -> bool:
    """Return True when the laptop is connected to external power."""
    try:
        for p in Path("/sys/class/power_supply").glob("*"):
            if (p / "type").read_text().strip() in ("Mains", "USB_PD", "USB"):
                online = (p / "online").read_text().strip()
                if online == "1":
                    return True
        return False
    except Exception:
        return True


def battery_percent() -> int | None:
    try:
        for p in Path("/sys/class/power_supply").glob("BAT*"):
            return int((p / "capacity").read_text().strip())
    except Exception:
        return None
    return None


def available_memory_gb() -> float:
    return psutil.virtual_memory().available / (1024 ** 3)