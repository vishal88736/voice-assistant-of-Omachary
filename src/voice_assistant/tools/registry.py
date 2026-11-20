"""Tool registry and base types."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict


@dataclass
class ToolResult:
    ok: bool
    data: Any = None
    error: str | None = None
    duration_ms: int = 0


@dataclass
class Tool:
    name: str
    description: str
    risk: str  # low | medium | high
    schema: dict
    func: Callable[[dict], ToolResult]
    audit: bool = True


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list(self) -> list[Tool]:
        return list(self._tools.values())

    def execute(self, name: str, args: dict, permission_manager) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(ok=False, error=f"Unknown tool: {name}")
        from ..security.permissions import Risk
        risk = Risk(tool.risk)
        desc = f"{tool.name}({args})"
        if not permission_manager.allowed(risk, desc):
            return ToolResult(ok=False, error="Permission denied")
        t0 = time.time()
        try:
            res = tool.func(args)
        except Exception as e:
            res = ToolResult(ok=False, error=str(e))
        res.duration_ms = int((time.time() - t0) * 1000)
        return res