"""Tests for power/resource helpers."""

from voice_assistant.system.power import available_memory_gb, battery_percent, on_ac_power


def test_power_helpers():
    assert isinstance(on_ac_power(), bool)
    assert available_memory_gb() > 0
    bp = battery_percent()
    assert bp is None or 0 <= bp <= 100