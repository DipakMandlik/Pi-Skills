from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class UserCreateRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    role: str = Field(default="MEMBER", max_length=50)


class UserUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = Field(default=None, max_length=50)
    status: str | None = Field(default=None, max_length=50)


class UserResponse(BaseModel):
    id: str
    org_id: str
    email: str
    name: str
    role: str
    status: str
    last_active: str | None = None
    created_at: str
    updated_at: str | None = None


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class UserSkillResponse(BaseModel):
    id: str
    name: str
    category: str
    status: str
    assigned_at: str


class InviteByEmailRequest(BaseModel):
    email: EmailStr
    role: str = Field(default="MEMBER", max_length=50)
