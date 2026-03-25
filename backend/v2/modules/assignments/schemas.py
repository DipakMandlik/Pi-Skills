from __future__ import annotations

from pydantic import BaseModel, Field


class AssignmentCreateRequest(BaseModel):
    skill_id: str
    assignee_type: str = Field(max_length=50)
    assignee_id: str
    expires_at: str | None = None


class AssignmentDeleteRequest(BaseModel):
    assignment_id: str


class AssignmentResponse(BaseModel):
    id: str
    skill_id: str
    skill_name: str
    assignee_type: str
    assignee_id: str
    assigned_by: str
    assigned_at: str
    expires_at: str | None = None


class AssignmentListResponse(BaseModel):
    assignments: list[AssignmentResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
