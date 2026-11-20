"""Tests for intent classifier."""

from voice_assistant.core.intent import classify


def test_volume_down():
    assert classify("volume kam karo") == ("volume", {"action": "down"})


def test_open_app():
    assert classify("terminal kholo") == ("open_app", {"name": "terminal"})


def test_open_vscode():
    r = classify("open vs code")
    assert r is not None and r[0] == "open_app"


def test_system_info():
    assert classify("battery status") == ("system_info", {})