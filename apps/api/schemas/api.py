from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ── Auth ────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    role: str
    user_id: str
    display_name: str


class UserMeResponse(BaseModel):
    user_id: str
    email: str
    role: str
    display_name: str
    allowed_models: list[str]
    allowed_skills: list[str]
    token_expires_at: str


# ── Users ───────────────────────────────────────────────────────────

class UserListItem(BaseModel):
    user_id: str
    email: str
    display_name: str
    role: str
    is_active: bool
    last_login_at: Optional[str] = None
    allowed_models: list[str]
    allowed_skills: list[str]


class UserListResponse(BaseModel):
    users: list[UserListItem]
    total: int
    page: int
    page_size: int


# ── Skills ──────────────────────────────────────────────────────────

class SkillAssignmentInfo(BaseModel):
    assigned_at: str
    expires_at: Optional[str] = None
    is_active: bool


class SkillResponse(BaseModel):
    skill_id: str
    display_name: str
    description: str
    required_models: list[str]
    is_active: bool
    assignment: Optional[SkillAssignmentInfo] = None


class SkillsListResponse(BaseModel):
    skills: list[SkillResponse]


class SkillAssignRequest(BaseModel):
    user_id: str
    skill_id: str = Field(min_length=1)
    expires_at: Optional[str] = None


class SkillAssignResponse(BaseModel):
    assignment_id: str
    user_id: str
    skill_id: str
    assigned_at: str
    expires_at: Optional[str] = None
    assigned_by: str


class SkillRevokeRequest(BaseModel):
    user_id: str
    skill_id: str = Field(min_length=1)


class SkillRevokeResponse(BaseModel):
    revoked: bool
    user_id: str
    skill_id: str
    revoked_at: str
    revoked_by: str


# ── Models ──────────────────────────────────────────────────────────

class ModelAccessInfo(BaseModel):
    granted_at: str
    expires_at: Optional[str] = None
    is_active: bool


class ModelListItem(BaseModel):
    model_id: str
    display_name: str
    provider: str
    tier: str
    is_available: bool
    access: Optional[ModelAccessInfo] = None


class ModelsListResponse(BaseModel):
    models: list[ModelListItem]


class ModelAssignRequest(BaseModel):
    user_id: str
    model_id: str = Field(min_length=1)
    expires_at: Optional[str] = None
    notes: Optional[str] = None


class ModelAssignResponse(BaseModel):
    permission_id: str
    user_id: str
    model_id: str
    granted_at: str
    expires_at: Optional[str] = None
    granted_by: str


class ModelRevokeRequest(BaseModel):
    user_id: str
    model_id: str = Field(min_length=1)


class ModelRevokeResponse(BaseModel):
    revoked: bool
    effective_immediately: bool
    cache_invalidated: bool


# ── Execute ─────────────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    skill_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    parameters: Optional[dict] = None
    max_tokens: int = Field(default=1000, ge=1, le=100000)


class ExecuteResponse(BaseModel):
    result: str
    model_id: str
    skill_id: str
    tokens_used: int
    latency_ms: int
    finish_reason: str
    request_id: str


# ── Monitoring ──────────────────────────────────────────────────────

class AuditLogEntry(BaseModel):
    id: str
    request_id: str
    user_id: Optional[str] = None
    skill_id: Optional[str] = None
    model_id: Optional[str] = None
    action: str
    outcome: str
    tokens_used: Optional[int] = None
    latency_ms: Optional[int] = None
    timestamp: str


class MonitoringSummary(BaseModel):
    total_executions: int
    total_denials: int
    total_tokens: int
    avg_latency_ms: float


class MonitoringResponse(BaseModel):
    logs: list[AuditLogEntry]
    total: int
    page: int
    page_size: int
    summary: MonitoringSummary


# ── Error ───────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    status: int
    title: str
    detail: str
    type: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: Optional[str] = None
