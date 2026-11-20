"""Tests for tools."""

from voice_assistant.config.settings import Settings
from voice_assistant.security.permissions import PermissionManager
from voice_assistant.tools.registry import ToolRegistry
from voice_assistant.tools.system_tools import register_all


def test_tool_registry():
    s = Settings()
    pm = PermissionManager(s)
    pm.settings.permissions["low"] = "auto"
    reg = ToolRegistry()
    register_all(reg, s, pm)
    assert reg.get("system_info") is not None
    res = reg.execute("system_info", {}, pm)
    assert res.ok is True


def test_unknown_tool():
    s = Settings()
    pm = PermissionManager(s)
    reg = ToolRegistry()
    res = reg.execute("nope", {}, pm)
    assert res.ok is False