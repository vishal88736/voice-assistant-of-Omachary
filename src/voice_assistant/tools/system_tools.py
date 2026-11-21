"""Concrete tool implementations."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..system.apps import open_app
from ..system.hyprland import (
    active_window,
    battery_info,
    close_app,
    cpu_ram_info,
    disk_info,
    focus_window,
    get_volume,
    list_windows,
    set_brightness,
    set_volume,
    switch_workspace,
    toggle_fullscreen,
)
from .registry import Tool, ToolResult


def _ok(data=None) -> ToolResult:
    return ToolResult(ok=True, data=data)


def _fail(msg: str) -> ToolResult:
    return ToolResult(ok=False, error=msg)


def register_all(registry, settings, permissions) -> None:
    # System info
    registry.register(Tool(
        name="system_info",
        description="Get battery, CPU, RAM, disk info",
        risk="low",
        schema={},
        func=lambda args: _ok({
            "battery": battery_info(),
            "cpu_ram": cpu_ram_info(),
            "disk": disk_info(),
            "volume": get_volume(),
        }),
    ))

    registry.register(Tool(
        name="open_app",
        description="Launch an application by friendly name",
        risk="low",
        schema={"name": "string"},
        func=lambda args: _ok(open_app(args.get("name", ""))) or _fail("Could not open app"),
    ))

    registry.register(Tool(
        name="close_window",
        description="Close a window by address",
        risk="medium",
        schema={"address": "string"},
        func=lambda args: _ok(close_app(args.get("address", ""))),
    ))

    registry.register(Tool(
        name="focus_window",
        description="Focus a window by address",
        risk="low",
        schema={"address": "string"},
        func=lambda args: _ok(focus_window(args.get("address", ""))),
    ))

    registry.register(Tool(
        name="list_windows",
        description="List open windows",
        risk="low",
        schema={},
        func=lambda args: _ok(list_windows()),
    ))

    registry.register(Tool(
        name="switch_workspace",
        description="Switch Hyprland workspace",
        risk="low",
        schema={"workspace": "string"},
        func=lambda args: _ok(switch_workspace(args.get("workspace", "1"))),
    ))

    registry.register(Tool(
        name="toggle_fullscreen",
        description="Toggle fullscreen on active window",
        risk="low",
        schema={},
        func=lambda args: _ok(toggle_fullscreen()),
    ))

    registry.register(Tool(
        name="volume",
        description="Adjust volume: up/down/mute or percentage",
        risk="low",
        schema={"action": "string"},
        func=lambda args: _handle_volume(args),
    ))

    registry.register(Tool(
        name="brightness",
        description="Adjust brightness",
        risk="low",
        schema={"value": "string"},
        func=lambda args: _ok(set_brightness(args.get("value", "+10%"))),
    ))

    registry.register(Tool(
        name="notify",
        description="Show a desktop notification",
        risk="low",
        schema={"title": "string", "body": "string"},
        func=lambda args: _ok(_notify(args)),
    ))

    registry.register(Tool(
        name="network_info",
        description="Show network status",
        risk="low",
        schema={},
        func=lambda args: _ok(_network_info()),
    ))

    registry.register(Tool(
        name="screenshot",
        description="Take a fullscreen screenshot",
        risk="low",
        schema={},
        func=lambda args: _ok(_screenshot()),
    ))

    registry.register(Tool(
        name="power",
        description="Lock, sleep, logout, reboot, or shut down (high risk)",
        risk="high",
        schema={"action": "string"},
        func=lambda args: _ok(_power(args)),
    ))

    registry.register(Tool(
        name="search_files",
        description="Search files by name in a directory",
        risk="low",
        schema={"query": "string", "root": "string"},
        func=lambda args: _ok(_search_files(args)),
    ))

    registry.register(Tool(
        name="read_file",
        description="Read a text file (size limited)",
        risk="medium",
        schema={"path": "string"},
        func=lambda args: _ok(_read_file(args)),
    ))

    registry.register(Tool(
        name="write_file",
        description="Create or edit a text file (requires confirmation)",
        risk="high",
        schema={"path": "string", "content": "string"},
        func=lambda args: _ok(_write_file(args)),
    ))

    registry.register(Tool(
        name="delete_path",
        description="Delete a file or empty directory (requires confirmation)",
        risk="high",
        schema={"path": "string"},
        func=lambda args: _ok(_delete_path(args)),
    ))

    registry.register(Tool(
        name="move_path",
        description="Move or rename a file (requires confirmation)",
        risk="high",
        schema={"src": "string", "dst": "string"},
        func=lambda args: _ok(_move_path(args)),
    ))

    registry.register(Tool(
        name="create_dir",
        description="Create a directory (requires confirmation)",
        risk="medium",
        schema={"path": "string"},
        func=lambda args: _ok(_create_dir(args)),
    ))

    registry.register(Tool(
        name="git_status",
        description="Git status for a repo path",
        risk="low",
        schema={"path": "string"},
        func=lambda args: _ok(_git_status(args)),
    ))

    registry.register(Tool(
        name="run_tests",
        description="Run approved test command in a project",
        risk="medium",
        schema={"path": "string", "command": "string"},
        func=lambda args: _ok(_run_tests(args)),
    ))


def _handle_volume(args: dict) -> ToolResult:
    action = args.get("action", "up").lower()
    if action in ("up", "raise", "increase"):
        ok = set_volume("+5%")
    elif action in ("down", "lower", "decrease", "kam"):
        ok = set_volume("-5%")
    elif action in ("mute", "toggle"):
        ok = set_volume("toggle")
    else:
        # assume percentage
        ok = set_volume(action)
    return ToolResult(ok=ok, data=get_volume())


def _notify(args: dict) -> str:
    title = args.get("title", "Voice Assistant")
    body = args.get("body", "")
    subprocess.Popen(["notify-send", title, body])
    return "Notification sent"


def _network_info() -> str:
    try:
        p = subprocess.run(["omarchy", "network", "status", "--verbose"], capture_output=True, text=True, timeout=10)
        return p.stdout.strip() or p.stderr.strip()
    except Exception as e:
        return f"error: {e}"


def _screenshot() -> str:
    out = Path("/tmp/opencode") / f"screenshot-{int(__import__('time').time())}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        p = subprocess.run(["grim", str(out)], capture_output=True, text=True, timeout=15)
        if p.returncode == 0 and out.exists():
            return str(out)
        return p.stderr.strip() or "Screenshot failed"
    except Exception as e:
        return f"error: {e}"


def _power(args: dict) -> str:
    action = args.get("action", "").lower()
    cmds = {
        "lock": ["loginctl", "lock-session"],
        "sleep": ["systemctl", "suspend"],
        "logout": ["omarchy", "system", "logout"],
        "reboot": ["omarchy", "system", "reboot"],
        "shutdown": ["omarchy", "system", "shutdown"],
    }
    if action not in cmds:
        return f"Unknown power action: {action}"
    try:
        subprocess.Popen(cmds[action])
        return f"Requested {action}"
    except Exception as e:
        return f"error: {e}"


def _search_files(args: dict) -> list[str]:
    query = args.get("query", "")
    root = args.get("root", str(Path.home()))
    results = []
    try:
        for p in Path(root).rglob(f"*{query}*"):
            results.append(str(p))
            if len(results) >= 50:
                break
    except Exception as e:
        return [f"error: {e}"]
    return results


def _read_file(args: dict) -> str:
    p = Path(args.get("path", "")).expanduser()
    if not p.is_file():
        return "File not found"
    try:
        data = p.read_text(errors="replace")
    except Exception as e:
        return f"error: {e}"
    if len(data) > 20000:
        data = data[:20000] + "\n...truncated..."
    return data


def _safe_path(raw: str) -> Path:
    p = Path(raw).expanduser()
    # resolve to catch traversal before touching anything
    return p.resolve(strict=False)


def _write_file(args: dict) -> str:
    p = _safe_path(args.get("path", ""))
    if not p.name:
        return "Invalid path"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(args.get("content", ""))
    return f"Wrote {p}"


def _delete_path(args: dict) -> str:
    p = _safe_path(args.get("path", ""))
    if not p.exists():
        return "Path not found"
    if p.is_dir():
        try:
            p.rmdir()
            return f"Removed empty directory {p}"
        except OSError:
            return "Directory is not empty; refusing to delete recursively"
    p.unlink()
    return f"Deleted {p}"


def _move_path(args: dict) -> str:
    src = _safe_path(args.get("src", ""))
    dst = _safe_path(args.get("dst", ""))
    if not src.exists():
        return "Source not found"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return f"Moved {src} -> {dst}"


def _create_dir(args: dict) -> str:
    p = _safe_path(args.get("path", ""))
    p.mkdir(parents=True, exist_ok=True)
    return f"Created {p}"


def _git_status(args: dict) -> str:
    path = args.get("path", ".")
    try:
        p = subprocess.run(["git", "-C", path, "status", "--short"], capture_output=True, text=True, timeout=15)
        return p.stdout.strip() or "clean"
    except Exception as e:
        return f"error: {e}"


def _run_tests(args: dict) -> str:
    path = args.get("path", ".")
    cmd = args.get("command", "pytest -q")
    # safety: only allow known test commands
    allowed = ["pytest", "npm test", "cargo test", "go test"]
    if not any(cmd.strip().startswith(a) for a in allowed):
        return "Test command not allowed"
    try:
        p = subprocess.run(cmd.split(), cwd=path, capture_output=True, text=True, timeout=300)
        return (p.stdout + p.stderr).strip()[:4000]
    except Exception as e:
        return f"error: {e}"