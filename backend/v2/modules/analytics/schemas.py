from __future__ import annotations

from pydantic import BaseModel


class TrendData(BaseModel):
    date: str
    value: int


class AnalyticsResponse(BaseModel):
    total_executions: int
    success_rate: float
    avg_duration_ms: float
    top_skills: list[dict]
    trends: list[TrendData]


class SkillUsageEntry(BaseModel):
    skill_id: str
    skill_name: str
    execution_count: int
    success_count: int
    error_count: int
    avg_duration_ms: float


class SkillErrorEntry(BaseModel):
    skill_id: str
    skill_name: str
    error: str
    count: int
    last_occurrence: str


class UserActivityEntry(BaseModel):
    user_id: str
    user_name: str
    execution_count: int
    last_active: str | None = None
