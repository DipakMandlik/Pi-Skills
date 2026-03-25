from __future__ import annotations

from pydantic import BaseModel, Field


class TeamCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=5000)


class TeamUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)


class TeamResponse(BaseModel):
    id: str
    org_id: str
    name: str
    description: str
    member_count: int
    created_at: str
    updated_at: str | None = None


class TeamMemberResponse(BaseModel):
    id: str
    user_id: str
    user_name: str
    user_email: str
    joined_at: str


class TeamSkillResponse(BaseModel):
    id: str
    name: str
    category: str
    status: str
    assigned_at: str


class AssignSkillsRequest(BaseModel):
    skill_ids: list[str] = Field(min_length=1)


class AddMembersRequest(BaseModel):
    user_ids: list[str] = Field(min_length=1)
