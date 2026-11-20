"""Concrete tool implementations."""

from __future__ import annotations

import os
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