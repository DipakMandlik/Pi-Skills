from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID
import re

from pydantic import BaseModel, EmailStr, Field, field_validator


MODEL_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,127}$")


def _validate_model_id(value: str) -> str:
    cleaned = value.strip()
    if not MODEL_ID_PATTERN.fullmatch(cleaned):
        raise ValueError("Invalid model_id format")
    return cleaned


# ── Auth ────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    role: str
    roles: list[str] = []
    user_id: str
    display_name: str


class UserMeResponse(BaseModel):
    user_id: str
    email: str
    role: str
    roles: list[str] = []
    display_name: str
    allowed_models: list[str]
    allowed_skills: list[str]
    rbac_permissions: Optional[dict[str, Any]] = None
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
    version: Optional[str] = None
    assignment: Optional[SkillAssignmentInfo] = None


class SkillsListResponse(BaseModel):
    skills: list[SkillResponse]


class SkillRegistryItemResponse(BaseModel):
    skill_id: str
    display_name: str
    description: str
    required_models: list[str]
    is_enabled: bool
    version: str
    input_schema: dict[str, Any]
    output_format: dict[str, Any]
    execution_handler: str
    error_handling: dict[str, Any]


class SkillRegistryResponse(BaseModel):
    skills: list[SkillRegistryItemResponse]


class SkillStateUpdateRequest(BaseModel):
    is_enabled: bool


class SkillStateUpdateResponse(BaseModel):
    skill_id: str
    is_enabled: bool
    updated_at: str


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


class SecretReferenceCreateRequest(BaseModel):
    reference_key: str = Field(min_length=3, max_length=255)
    provider: str = Field(min_length=2, max_length=100)
    secret_value: str = Field(min_length=8)


class SecretReferenceResponse(BaseModel):
    reference_key: str
    provider: str
    is_active: bool
    created_at: str


class SecretReferenceListResponse(BaseModel):
    references: list[SecretReferenceResponse]


class ModelConfigurationCreateRequest(BaseModel):
    model_id: str = Field(min_length=1)
    provider: str = Field(min_length=2, max_length=100)
    base_url: str = Field(min_length=4, max_length=500)
    secret_reference_key: str = Field(min_length=3, max_length=255)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=100000)
    request_timeout_seconds: int = Field(default=30, ge=1, le=300)
    parameters: dict[str, Any] = Field(default_factory=dict)


class ModelConfigurationUpdateRequest(BaseModel):
    base_url: Optional[str] = Field(default=None, min_length=4, max_length=500)
    secret_reference_key: Optional[str] = Field(default=None, min_length=3, max_length=255)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=100000)
    request_timeout_seconds: Optional[int] = Field(default=None, ge=1, le=300)
    parameters: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class ModelConfigurationResponse(BaseModel):
    id: str
    model_id: str
    provider: str
    base_url: str
    secret_reference_key: str
    temperature: float
    max_tokens: int
    request_timeout_seconds: int
    parameters: dict[str, Any]
    is_active: bool
    created_at: str
    updated_at: Optional[str] = None


class ModelConfigurationListResponse(BaseModel):
    configs: list[ModelConfigurationResponse]


class ModelConnectivityValidationRequest(BaseModel):
    provider: str = Field(min_length=2, max_length=100)
    base_url: str = Field(min_length=4, max_length=500)
    secret_reference_key: str = Field(min_length=3, max_length=255)


class ModelConnectivityValidationResponse(BaseModel):
    valid: bool
    provider: str
    base_url: str
    latency_ms: int
    message: str


# ── Execute ─────────────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    skill_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    parameters: Optional[dict] = None
    max_tokens: int = Field(default=1000, ge=1, le=100000)

    @field_validator("model_id")
    @classmethod
    def validate_model_id(cls, value: str) -> str:
        return _validate_model_id(value)


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


# ── Governance ───────────────────────────────────────────────────────

class GovernanceRequest(BaseModel):
    prompt: str = Field(min_length=1)
    model_id: Optional[str] = None
    task_type: str = Field(default="general")
    skill_id: Optional[str] = None
    max_tokens: int = Field(default=1000, ge=1, le=100000)
    parameters: Optional[dict] = None

    @field_validator("model_id")
    @classmethod
    def validate_model_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return _validate_model_id(value)


class GovernanceResponse(BaseModel):
    status: str
    request_id: str
    result: Optional[str] = None
    model_id: Optional[str] = None
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    latency_ms: int
    finish_reason: Optional[str] = None
    remaining_tokens: Optional[int] = None
    reason: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class GovernanceValidateRequest(BaseModel):
    model_id: Optional[str] = None
    task_type: str = Field(default="general")
    estimated_tokens: int = Field(default=1000, ge=1)

    @field_validator("model_id")
    @classmethod
    def validate_model_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return _validate_model_id(value)


class GovernanceValidateResponse(BaseModel):
    valid: bool
    model_id: Optional[str] = None
    reason: Optional[str] = None
    message: Optional[str] = None


# ── Subscriptions ────────────────────────────────────────────────────

class SubscriptionCreateRequest(BaseModel):
    plan_name: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=255)
    monthly_token_limit: int = Field(ge=1)
    max_tokens_per_request: int = Field(default=4096, ge=1)
    allowed_models: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    priority: str = Field(default="standard")
    rate_limit_per_minute: int = Field(default=60, ge=1)
    cost_budget_monthly: float = Field(default=0.0, ge=0)


class SubscriptionResponse(BaseModel):
    plan_name: str
    display_name: str
    monthly_token_limit: int
    max_tokens_per_request: int
    allowed_models: list[str]
    features: list[str]
    priority: str
    rate_limit_per_minute: int
    cost_budget_monthly: float


class SubscriptionListResponse(BaseModel):
    subscriptions: list[SubscriptionResponse]
    total: int


class SubscriptionAssignRequest(BaseModel):
    user_id: str
    plan_name: str = Field(min_length=1)


class SubscriptionAssignResponse(BaseModel):
    user_id: str
    plan_name: str
    assigned_at: Optional[str] = None


# ── Token Usage ──────────────────────────────────────────────────────

class TokenUsageResponse(BaseModel):
    user_id: str
    period: str
    tokens_used: int
    tokens_limit: int
    cost_accumulated: float
    remaining_tokens: int


class TokenUsageStatsResponse(BaseModel):
    user_id: str
    period: str
    usage: Optional[TokenUsageResponse] = None
    model_breakdown: list[dict] = Field(default_factory=list)


# ── Model Access Control ─────────────────────────────────────────────

class ModelAccessControlRequest(BaseModel):
    model_id: str = Field(min_length=1)
    allowed_roles: list[str] = Field(default_factory=list)
    max_tokens_per_request: int = Field(default=4096, ge=1)
    enabled: bool = True
    rate_limit_per_minute: int = Field(default=60, ge=1)


class ModelAccessControlResponse(BaseModel):
    model_id: str
    allowed_roles: list[str]
    max_tokens_per_request: int
    enabled: bool
    rate_limit_per_minute: int


class ModelAccessControlListResponse(BaseModel):
    configs: list[ModelAccessControlResponse]
    total: int


# ── Feature Flags ────────────────────────────────────────────────────

class FeatureFlagRequest(BaseModel):
    feature_name: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    enabled: bool = True
    enabled_for: list[str] = Field(default_factory=list)
    config: dict = Field(default_factory=dict)


class FeatureFlagResponse(BaseModel):
    feature_name: str
    model_id: str
    enabled: bool
    enabled_for: list[str]
    config: dict


# ── User Dashboard ───────────────────────────────────────────────────

class UserDashboardResponse(BaseModel):
    user_id: str
    subscription: Optional[dict] = None
    token_usage: Optional[TokenUsageResponse] = None
    usage_stats: Optional[TokenUsageStatsResponse] = None


# ── System Overview ──────────────────────────────────────────────────

class SystemOverviewResponse(BaseModel):
    subscriptions: list[SubscriptionResponse]
    model_access_configs: list[ModelAccessControlResponse]
    total_subscriptions: int
    total_models_configured: int


# ── Subscription Update ──────────────────────────────────────────────

class SubscriptionUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    monthly_token_limit: Optional[int] = Field(default=None, ge=1)
    max_tokens_per_request: Optional[int] = Field(default=None, ge=1)
    allowed_models: Optional[list[str]] = None
    features: Optional[list[str]] = None
    priority: Optional[str] = None
    rate_limit_per_minute: Optional[int] = Field(default=None, ge=1)
    cost_budget_monthly: Optional[float] = Field(default=None, ge=0)


class SubscriptionDeleteResponse(BaseModel):
    plan_name: str
    deleted: bool


# ── User Subscription List ───────────────────────────────────────────

class UserSubscriptionListItem(BaseModel):
    user_id: str
    plan_name: str
    assigned_at: Optional[str] = None
    assigned_by: Optional[str] = None


class UserSubscriptionListResponse(BaseModel):
    user_subscriptions: list[UserSubscriptionListItem]
    total: int


# ── Budget Alert ─────────────────────────────────────────────────────

class BudgetAlertResponse(BaseModel):
    alert: bool
    level: str
    cost_used: float
    cost_budget: float
    percentage: float
    period: str


# ── Usage Trend ──────────────────────────────────────────────────────

class UsageTrendItem(BaseModel):
    period: str
    tokens_used: int
    tokens_limit: int
    cost_accumulated: float


class UsageTrendResponse(BaseModel):
    trend: list[UsageTrendItem]
    months: int


# ── Global Stats ─────────────────────────────────────────────────────

class GlobalStatsResponse(BaseModel):
    period: str
    total_tokens: int
    total_cost: float
    total_requests: int
    unique_users: int
    model_breakdown: list[dict]


# ── Token Reset ──────────────────────────────────────────────────────

class TokenResetRequest(BaseModel):
    user_id: str
    new_limit: int = Field(ge=1)


class TokenResetResponse(BaseModel):
    status: str
    user_id: str
    period: str
    new_limit: int


# ── Usage Logs ───────────────────────────────────────────────────────

class UsageLogEntry(BaseModel):
    id: str
    user_id: str
    model_id: str
    skill_id: Optional[str] = None
    tokens_used: int
    cost: float
    request_id: Optional[str] = None
    latency_ms: Optional[int] = None
    outcome: str
    timestamp: Optional[str] = None


class UsageLogsResponse(BaseModel):
    logs: list[UsageLogEntry]
    total: int
    offset: int
    limit: int


# ── Governance Policies ─────────────────────────────────────────────

class PolicyCreateRequest(BaseModel):
    policy_name: str = Field(min_length=1, max_length=255)
    policy_type: str = Field(min_length=1)
    description: str = ""
    conditions: dict = Field(default_factory=dict)
    actions: dict = Field(default_factory=dict)
    priority: str = "standard"
    enabled: bool = True


class PolicyUpdateRequest(BaseModel):
    description: Optional[str] = None
    conditions: Optional[dict] = None
    actions: Optional[dict] = None
    priority: Optional[str] = None
    enabled: Optional[bool] = None


class PolicyResponse(BaseModel):
    id: str
    policy_name: str
    policy_type: str
    description: str
    conditions: dict
    actions: dict
    priority: str
    enabled: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PolicyListResponse(BaseModel):
    policies: list[PolicyResponse]
    total: int


class PolicyEvaluateRequest(BaseModel):
    user_id: str
    user_role: str
    model_id: str
    task_type: str = "general"
    estimated_tokens: int = 1000
    context: Optional[dict] = None


class PolicyEvaluateResponse(BaseModel):
    allowed: bool
    violations: list[dict]
    warnings: list[dict]
    policies_evaluated: int


# ── Bulk Operations ──────────────────────────────────────────────────

class BulkUserAssignRequest(BaseModel):
    user_ids: list[str]
    plan_name: str = Field(min_length=1)


class BulkUserAssignResponse(BaseModel):
    assigned: list[str]
    failed: list[dict]
    total: int


class DeleteResponse(BaseModel):
    deleted: bool
    message: str


# ── Skill CRUD (Admin) ──────────────────────────────────────────────

class SkillCreateRequest(BaseModel):
    skill_id: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=5000)
    skill_type: str = Field(default="ai")  # ai, sql, hybrid, system
    domain: str = Field(default="general")
    required_models: list[str] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_format: dict[str, Any] = Field(default_factory=dict)
    execution_handler: str = Field(default="")
    error_handling: dict[str, Any] = Field(default_factory=dict)
    instructions: str = Field(default="")
    is_enabled: bool = True


class SkillUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    skill_type: Optional[str] = None
    domain: Optional[str] = None
    required_models: Optional[list[str]] = None
    input_schema: Optional[dict[str, Any]] = None
    output_format: Optional[dict[str, Any]] = None
    execution_handler: Optional[str] = None
    error_handling: Optional[dict[str, Any]] = None
    instructions: Optional[str] = None
    is_enabled: Optional[bool] = None


class SkillFullResponse(BaseModel):
    skill_id: str
    display_name: str
    description: str
    skill_type: str
    domain: str
    required_models: list[str]
    is_enabled: bool
    version: str
    input_schema: dict[str, Any]
    output_format: dict[str, Any]
    execution_handler: str
    error_handling: dict[str, Any]
    instructions: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    assignment_count: int = 0


class SkillsPaginatedResponse(BaseModel):
    skills: list[SkillFullResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SkillDeleteResponse(BaseModel):
    deleted: bool
    skill_id: str
    message: str
