from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SkillCreateRequest(BaseModel):
    name: str = Field(default="", min_length=0, max_length=255)
    display_name: str = Field(default="", min_length=0, max_length=255)
    description: str = Field(default="", max_length=5000)
    content: str = Field(default="", max_length=50000)
    instructions: str = Field(default="", max_length=50000)
    category: str = Field(default="general", max_length=100)
    skill_type: str = Field(default="", max_length=100)
    domain: str = Field(default="general", max_length=100)
    required_models: list[str] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_format: dict[str, Any] = Field(default_factory=dict)
    execution_handler: str = Field(default="")
    error_handling: dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool = Field(default=True)


class SkillUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=0, max_length=255)
    display_name: str | None = Field(default=None, min_length=0, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    content: str | None = Field(default=None, max_length=50000)
    instructions: str | None = Field(default=None, max_length=50000)
    category: str | None = Field(default=None, max_length=100)
    skill_type: str | None = Field(default=None, max_length=100)
    domain: str | None = Field(default=None, max_length=100)
    required_models: list[str] | None = None
    input_schema: dict[str, Any] | None = None
    output_format: dict[str, Any] | None = None
    execution_handler: str | None = None
    error_handling: dict[str, Any] | None = None
    is_enabled: bool | None = None


class SkillResponse(BaseModel):
    id: str
    skill_id: str
    org_id: str
    name: str
    display_name: str
    description: str
    content: str
    instructions: str
    category: str
    skill_type: str
    domain: str
    status: str
    is_enabled: bool
    version: str
    created_by: str
    created_at: str
    updated_at: str | None = None
    required_models: list[str]
    input_schema: dict[str, Any]
    output_format: dict[str, Any]
    execution_handler: str
    error_handling: dict[str, Any]
    assignment_count: int = 0


class SkillVersionResponse(BaseModel):
    id: str
    skill_id: str
    content: str
    version: int
    created_by: str
    created_at: str


class SkillAssignmentResponse(BaseModel):
    id: str
    skill_id: str
    assignee_type: str
    assignee_id: str
    assigned_by: str
    assigned_at: str
    expires_at: str | None = None


class SkillExecutionRequest(BaseModel):
    input_data: dict = Field(default_factory=dict)


class SkillExecutionResponse(BaseModel):
    id: str
    skill_id: str
    user_id: str
    status: str
    output_data: dict | None = None
    duration_ms: int | None = None
    created_at: str
