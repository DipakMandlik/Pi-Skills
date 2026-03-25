from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AuthUser:
    user_id: str
    email: str
    role: str
    display_name: str
    request_id: str = ""
    token_exp: int = 0


@dataclass
class UserPermissions:
    user_id: str
    allowed_models: list[str] = field(default_factory=list)
    allowed_skills: list[str] = field(default_factory=list)


@dataclass
class GuardContext:
    user_id: str
    role: str
    skill_id: str
    model_id: str
    request_id: str
    started_at: float


class GuardDenied(Exception):
    def __init__(self, reason: str, message: str = ""):
        self.reason = reason
        self.message = message or reason
        super().__init__(self.message)


class ModelInvocationError(Exception):
    pass


@dataclass
class ModelResult:
    content: str
    tokens_used: int
    model_id: str
    finish_reason: str = "end_turn"
