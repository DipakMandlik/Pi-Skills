from __future__ import annotations

from pydantic import BaseModel, Field


class OrgUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    settings: dict | None = None


class OrgResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    settings: dict
    created_at: str
    updated_at: str | None = None


class ActivityEntry(BaseModel):
    id: str
    user_id: str
    user_name: str
    action: str
    resource_type: str
    resource_id: str | None = None
    metadata_: dict
    created_at: str


class OrgStatsResponse(BaseModel):
    total_users: int
    total_teams: int
    total_skills: int
    total_assignments: int
    active_skills: int
    draft_skills: int
