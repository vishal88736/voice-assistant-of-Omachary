"""Deterministic intent classifier for common commands (no LLM)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


def classify(text: str) -> Optional[tuple[str, dict]]:
    t = text.lower().strip()
    # volume
    if any(k in t for k in ["volume", "awaz", "awaaz", "sound"]) and any(k in t for k in ["kam", "down", "lower", "decrease", "thoda"]):
        return ("volume", {"action": "down"})
    if any(k in t for k in ["volume", "awaz", "awaaz", "sound"]) and any(k in t for k in ["badha", "up", "raise", "increase", "tez"]):
        return ("volume", {"action": "up"})
    if "mute" in t:
        return ("volume", {"action": "mute"})
    # brightness
    if any(k in t for k in ["brightness", "screen light", "display"]) and any(k in t for k in ["kam", "down", "lower"]):
        return ("brightness", {"value": "-10%"})
    if any(k in t for k in ["brightness", "screen light", "display"]) and any(k in t for k in ["badha", "up", "raise", "increase"]):
        return ("brightness", {"value": "+10%"})
    # open app
    m = re.search(r"(?:open|kholo|launch|start)\s+(.+)", t)
    if m:
        target = m.group(1).strip().rstrip(".")
        # workspace? 
        if "workspace" in target:
            ws = "".join(ch for ch in target if ch.isdigit()) or "1"
            return ("switch_workspace", {"workspace": ws})
        # terminal etc
        for app in ["vs code", "vscode", "code", "terminal", "chrome", "chromium", "brave", "firefox", "files", "file manager", "spotify", "ghostty", "kitty", "alacritty"]:
            if app in target:
                return ("open_app", {"name": app})
        # if target is single known app
        return ("open_app", {"name": target})
    # hindi style: "X kholo" already caught by kholo in regex? regex open|kholo yes if kholo before target? "terminal kholo" not match because kholo after. Handle.
    m = re.search(r"(.+?)\s+(?:kholo|khol do|open kar|launch kar)", t)
    if m:
        target = m.group(1).strip()
        if "workspace" in target:
            ws = "".join(ch for ch in target if ch.isdigit()) or "1"
            return ("switch_workspace", {"workspace": ws})
        return ("open_app", {"name": target})
    # workspace switch
    if "workspace" in t and any(k in t for k in ["switch", "jao", "pe jao", "next", "previous", "prev"]):
        ws = "".join(ch for ch in t if ch.isdigit())
        if "next" in t:
            return ("switch_workspace", {"workspace": "+1"})
        if "prev" in t or "previous" in t:
            return ("switch_workspace", {"workspace": "-1"})
        if ws:
            return ("switch_workspace", {"workspace": ws})
    # system info
    if any(k in t for k in ["battery", "ram", "cpu", "system info", "storage", "disk"]):
        return ("system_info", {})
    if "network" in t or "wifi" in t or "internet" in t:
        return ("network_info", {})
    if "screenshot" in t or "screen shot" in t:
        return ("screenshot", {})
    if "lock screen" in t or "screen lock" in t:
        return ("power", {"action": "lock"})
    if any(k in t for k in ["shutdown", "shut down", "power off"]):
        return ("power", {"action": "shutdown"})
    if "reboot" in t or "restart laptop" in t:
        return ("power", {"action": "reboot"})
    # file operations (permission-gated)
    m = re.search(r"(?:delete|remove|hatao|mita do)\s+(?:file\s+)?(.+)", t)
    if m:
        return ("delete_path", {"path": m.group(1).strip()})
    m = re.search(r"(?:rename|move)\s+(.+?)\s+to\s+(.+)", t)
    if m:
        return ("move_path", {"src": m.group(1).strip(), "dst": m.group(2).strip()})
    m = re.search(r"(?:create|make|banao)\s+(?:folder|directory|dir)\s+(.+)", t)
    if m:
        return ("create_dir", {"path": m.group(1).strip()})
    # fullscreen
    if "fullscreen" in t:
        return ("toggle_fullscreen", {})
    # close
    m = re.search(r"close\s+(.+)", t)
    if m:
        # not enough info for address; list windows instead
        return ("list_windows", {})
    # git status
    if "git status" in t or "git check" in t:
        return ("git_status", {"path": "."})
    # search files
    m = re.search(r"(?:search|find|dhundho)\s+(?:file|files)?\s*(.+)", t)
    if m and any(k in t for k in ["file", "files", "dhundho", "search", "find"]):
        q = m.group(1).strip()
        if q and q not in ("file", "files"):
            return ("search_files", {"query": q, "root": str(Path.home()) if False else "."})
    return None