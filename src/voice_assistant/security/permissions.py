"""Permission management for tool execution."""

from __future__ import annotations

from enum import Enum
from typing import Callable


class Risk(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PermissionManager:
    def __init__(self, settings, confirm_callback: Callable[[str, Risk], bool] | None = None):
        self.settings = settings
        self.confirm = confirm_callback or (lambda _desc, _risk: False)

    def policy(self, risk: Risk) -> str:
        return self.settings.permissions.get(risk.value, "confirm")

    def allowed(self, risk: Risk, description: str) -> bool:
        policy = self.policy(risk)
        if policy == "auto":
            return True
        if policy == "deny":
            return False
        # confirm
        return bool(self.confirm(description, risk))