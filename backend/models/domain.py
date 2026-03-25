from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AuthUser:
    user_id: str
    email: str
    role: str
    display_name: str
    request_id: str = ""
    token_exp: int = 0
    roles: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.roles:
            self.roles = [self.role]
        # Normalize roles to uppercase
        self.roles = [r.upper() for r in self.roles]
        self.role = self.role.upper()

    def has_role(self, role: str) -> bool:
        return role.upper() in self.roles

    def has_any_role(self, *role_names: str) -> bool:
        allowed = {r.upper() for r in role_names}
        return bool(set(self.roles) & allowed)


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
