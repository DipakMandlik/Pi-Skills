"""Skill Registry Service — full CRUD with DB-backed skills."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import SkillAssignmentModel, SkillDefinitionModel, SkillStateModel

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SkillDefinition:
    skill_id: str
    display_name: str
    description: str
    skill_type: str = "ai"
    domain: str = "general"
    required_models: list[str] = None
    version: str = "1.0.0"
    is_enabled: bool = True
    input_schema: dict[str, Any] = None
    output_format: dict[str, Any] = None
    execution_handler: str = ""
    error_handling: dict[str, Any] = None
    instructions: str = ""

    def __post_init__(self):
        object.__setattr__(self, "required_models", self.required_models or [])
        object.__setattr__(self, "input_schema", self.input_schema or {})
        object.__setattr__(self, "output_format", self.output_format or {})
        object.__setattr__(self, "error_handling", self.error_handling or {})


# ── Default seed skills (only used when DB is empty) ────────────────

_DEFAULT_SKILLS: list[SkillDefinition] = [
    SkillDefinition(
        skill_id="skill_summarizer",
        display_name="Document Summarizer",
        description="Summarizes long documents into key points",
        skill_type="ai",
        domain="content",
        required_models=["claude-3-haiku-20240307", "claude-3-5-sonnet-20241022"],
        version="1.0.0",
        is_enabled=True,
        input_schema={"type": "object", "required": ["prompt"], "properties": {"prompt": {"type": "string"}, "style": {"type": "string", "enum": ["brief", "detailed"], "default": "brief"}}},
        output_format={"content_type": "text/markdown", "shape": {"summary": "string", "highlights": ["string"]}},
        execution_handler="backend.services.execution_handler:run_skill_summarizer",
        error_handling={"retryable_errors": ["provider_timeout"], "fallback": "return_compact_summary"},
        instructions="You are a document summarization expert. Read the provided text and produce a concise summary with key bullet points.",
    ),
    SkillDefinition(
        skill_id="skill_analyst",
        display_name="Data Analyst",
        description="Analyzes structured data and provides insights",
        skill_type="ai",
        domain="analytics",
        required_models=["claude-3-5-sonnet-20241022", "gemini-1.5-pro"],
        version="1.0.0",
        is_enabled=True,
        input_schema={"type": "object", "required": ["prompt"], "properties": {"prompt": {"type": "string"}, "data_context": {"type": "array", "items": {"type": "string"}}}},
        output_format={"content_type": "application/json", "shape": {"insights": ["string"], "risks": ["string"], "actions": ["string"]}},
        execution_handler="backend.services.execution_handler:run_skill_analyst",
        error_handling={"retryable_errors": ["provider_timeout", "rate_limited"], "fallback": "return_partial_insights"},
        instructions="You are a data analyst. Analyze the provided data and return actionable insights, risks, and recommended actions.",
    ),
    SkillDefinition(
        skill_id="skill_coder",
        display_name="Code Assistant",
        description="Generates, reviews, and explains code",
        skill_type="ai",
        domain="engineering",
        required_models=["claude-3-5-sonnet-20241022", "gpt-4o"],
        version="1.0.0",
        is_enabled=True,
        input_schema={"type": "object", "required": ["prompt"], "properties": {"prompt": {"type": "string"}, "language": {"type": "string", "default": "python"}}},
        output_format={"content_type": "text/markdown", "shape": {"code": "string", "explanation": "string", "warnings": ["string"]}},
        execution_handler="backend.services.execution_handler:run_skill_coder",
        error_handling={"retryable_errors": ["provider_timeout"], "fallback": "return_outline"},
        instructions="You are an expert software engineer. Generate clean, well-documented code with explanations and warnings about potential issues.",
    ),
    SkillDefinition(
        skill_id="skill_translator",
        display_name="Language Translator",
        description="Translates text between languages",
        skill_type="ai",
        domain="language",
        required_models=["claude-3-haiku-20240307", "gemini-1.5-pro"],
        version="1.0.0",
        is_enabled=True,
        input_schema={"type": "object", "required": ["prompt"], "properties": {"prompt": {"type": "string"}, "target_language": {"type": "string", "minLength": 2}}},
        output_format={"content_type": "application/json", "shape": {"translated_text": "string", "detected_language": "string"}},
        execution_handler="backend.services.execution_handler:run_skill_translator",
        error_handling={"retryable_errors": ["provider_timeout"], "fallback": "return_source_text"},
        instructions="You are a professional translator. Translate the provided text accurately while preserving tone and context.",
    ),
    SkillDefinition(
        skill_id="skill_sql_writer",
        display_name="SQL Writer",
        description="Generates and optimizes SQL queries for Snowflake",
        skill_type="sql",
        domain="data",
        required_models=["claude-3-5-sonnet-20241022"],
        version="1.0.0",
        is_enabled=True,
        input_schema={"type": "object", "required": ["prompt"], "properties": {"prompt": {"type": "string"}, "database": {"type": "string"}, "tables": {"type": "array", "items": {"type": "string"}}}},
        output_format={"content_type": "text/sql", "shape": {"query": "string", "explanation": "string"}},
        execution_handler="backend.services.execution_handler:run_sql_writer",
        error_handling={"retryable_errors": ["provider_timeout"], "fallback": "return_query_outline"},
        instructions="You are a Snowflake SQL expert. Generate efficient, well-formatted SQL queries using CTEs, proper JOINs, and Snowflake-specific features.",
    ),
    SkillDefinition(
        skill_id="skill_data_architect",
        display_name="Data Architect",
        description="Designs data models, schemas, and DDL for analytics platforms",
        skill_type="hybrid",
        domain="architecture",
        required_models=["claude-3-5-sonnet-20241022"],
        version="1.0.0",
        is_enabled=True,
        input_schema={"type": "object", "required": ["prompt"], "properties": {"prompt": {"type": "string"}, "paradigm": {"type": "string", "enum": ["dimensional", "data_vault", "medallion", "3NF"]}}},
        output_format={"content_type": "application/json", "shape": {"entities": ["object"], "relationships": ["object"], "ddl": ["string"]}},
        execution_handler="backend.services.execution_handler:run_data_architect",
        error_handling={"retryable_errors": ["provider_timeout"], "fallback": "return_partial_design"},
        instructions="You are a senior data architect. Design robust, scalable data models following industry best practices (Kimball, Data Vault, Medallion).",
    ),
    SkillDefinition(
        skill_id="skill_query_optimizer",
        display_name="Query Optimizer",
        description="Analyzes and optimizes SQL query performance",
        skill_type="sql",
        domain="performance",
        required_models=["claude-3-5-sonnet-20241022"],
        version="1.0.0",
        is_enabled=True,
        input_schema={"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}, "explain_plan": {"type": "string"}}},
        output_format={"content_type": "application/json", "shape": {"optimized_query": "string", "recommendations": ["string"], "estimated_improvement": "string"}},
        execution_handler="backend.services.execution_handler:run_query_optimizer",
        error_handling={"retryable_errors": ["provider_timeout"], "fallback": "return_basic_tips"},
        instructions="You are a Snowflake performance tuning expert. Analyze queries for optimization opportunities including clustering, materialized views, and query restructuring.",
    ),
    SkillDefinition(
        skill_id="skill_security_analyst",
        display_name="Security Analyst",
        description="Reviews data access patterns and identifies security risks",
        skill_type="ai",
        domain="security",
        required_models=["claude-3-5-sonnet-20241022"],
        version="1.0.0",
        is_enabled=True,
        input_schema={"type": "object", "required": ["prompt"], "properties": {"prompt": {"type": "string"}, "context": {"type": "object"}}},
        output_format={"content_type": "application/json", "shape": {"risks": ["object"], "recommendations": ["string"], "compliance_status": "string"}},
        execution_handler="backend.services.execution_handler:run_security_analyst",
        error_handling={"retryable_errors": ["provider_timeout"], "fallback": "return_basic_checklist"},
        instructions="You are a data security analyst. Review access patterns, identify PII exposure risks, and recommend RBAC improvements.",
    ),
    SkillDefinition(
        skill_id="skill_cost_optimizer",
        display_name="Cost Optimizer",
        description="Analyzes and optimizes AI model usage costs",
        skill_type="ai",
        domain="governance",
        required_models=["claude-3-haiku-20240307"],
        version="1.0.0",
        is_enabled=True,
        input_schema={"type": "object", "required": ["prompt"], "properties": {"prompt": {"type": "string"}, "current_model": {"type": "string"}, "budget": {"type": "number"}}},
        output_format={"content_type": "application/json", "shape": {"recommended_model": "string", "estimated_savings": "number", "quality_impact": "string"}},
        execution_handler="backend.services.execution_handler:run_cost_optimizer",
        error_handling={"retryable_errors": ["provider_timeout"], "fallback": "return_cost_comparison"},
        instructions="You are a cost optimization expert. Analyze AI model usage and recommend the most cost-effective model for each task while maintaining quality.",
    ),
    SkillDefinition(
        skill_id="skill_data_quality",
        display_name="Data Quality Engineer",
        description="Validates data quality and identifies anomalies",
        skill_type="hybrid",
        domain="quality",
        required_models=["claude-3-5-sonnet-20241022"],
        version="1.0.0",
        is_enabled=True,
        input_schema={"type": "object", "required": ["prompt"], "properties": {"prompt": {"type": "string"}, "table_name": {"type": "string"}, "checks": {"type": "array", "items": {"type": "string"}}}},
        output_format={"content_type": "application/json", "shape": {"checks_passed": "number", "checks_failed": "number", "issues": ["object"], "sql_tests": ["string"]}},
        execution_handler="backend.services.execution_handler:run_data_quality",
        error_handling={"retryable_errors": ["provider_timeout"], "fallback": "return_basic_checks"},
        instructions="You are a data quality engineer. Design comprehensive data quality checks including null checks, uniqueness, referential integrity, and anomaly detection.",
    ),
]


def get_default_registry_items() -> list[SkillDefinition]:
    return list(_DEFAULT_SKILLS)


def _parse_version_tuple(version: str) -> tuple[int, ...]:
    parts = []
    for token in version.split("."):
        try:
            parts.append(int(token))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _latest_definitions(definitions: list[SkillDefinitionModel]) -> list[SkillDefinitionModel]:
    by_skill: dict[str, SkillDefinitionModel] = {}
    for item in definitions:
        current = by_skill.get(item.skill_id)
        if current is None or _parse_version_tuple(item.version) > _parse_version_tuple(current.version):
            by_skill[item.skill_id] = item
    return list(by_skill.values())


def _map_db_skill(defn: SkillDefinitionModel, state: SkillStateModel | None) -> SkillDefinition:
    return SkillDefinition(
        skill_id=defn.skill_id,
        display_name=defn.display_name,
        description=defn.description or "",
        skill_type=getattr(defn, "skill_type", "ai") or "ai",
        domain=getattr(defn, "domain", "general") or "general",
        required_models=list(defn.required_models or []),
        version=defn.version,
        is_enabled=state.is_enabled if state is not None else True,
        input_schema=dict(defn.input_schema or {}),
        output_format=dict(defn.output_format or {}),
        execution_handler=defn.execution_handler or "",
        error_handling=dict(defn.error_handling or {}),
        instructions=getattr(defn, "instructions", "") or "",
    )


async def list_skills_db(db: AsyncSession, include_disabled: bool = False) -> list[SkillDefinition]:
    """List all skills from DB, falling back to defaults if DB is empty."""
    defs_result = await db.execute(select(SkillDefinitionModel))
    all_defs = defs_result.scalars().all()

    if not all_defs:
        items = sorted(_DEFAULT_SKILLS, key=lambda s: s.display_name.lower())
        if include_disabled:
            return items
        return [item for item in items if item.is_enabled]

    latest_defs = _latest_definitions(all_defs)
    states_result = await db.execute(select(SkillStateModel))
    state_rows = states_result.scalars().all()
    state_map = {(s.skill_id, s.version): s for s in state_rows}

    items = [
        _map_db_skill(defn, state_map.get((defn.skill_id, defn.version)))
        for defn in latest_defs
    ]
    items.sort(key=lambda s: s.display_name.lower())
    if include_disabled:
        return items
    return [item for item in items if item.is_enabled]


async def get_skill_db(db: AsyncSession, skill_id: str) -> SkillDefinition | None:
    items = await list_skills_db(db, include_disabled=True)
    for item in items:
        if item.skill_id == skill_id:
            return item
    return None


async def set_skill_enabled_db(
    db: AsyncSession,
    skill_id: str,
    is_enabled: bool,
    updated_by: str,
) -> SkillDefinition | None:
    skill = await get_skill_db(db, skill_id)
    if skill is None:
        return None

    state_result = await db.execute(
        select(SkillStateModel).where(
            SkillStateModel.skill_id == skill.skill_id,
            SkillStateModel.version == skill.version,
        )
    )
    state = state_result.scalar_one_or_none()
    if state is None:
        state = SkillStateModel(
            skill_id=skill.skill_id,
            version=skill.version,
            is_enabled=is_enabled,
            skill_type=skill.skill_type,
            domain=skill.domain,
            updated_by=updated_by,
        )
        db.add(state)
    else:
        state.is_enabled = is_enabled
        state.updated_by = updated_by

    await db.commit()
    return await get_skill_db(db, skill_id)


# ── Full CRUD operations ────────────────────────────────────────────

async def create_skill_db(
    db: AsyncSession,
    data: dict[str, Any],
    created_by: str,
) -> SkillDefinition:
    """Create a new skill in the database."""
    skill_id = data["skill_id"]
    version = data.get("version", "1.0.0")

    # Check if skill already exists
    existing = await db.execute(
        select(SkillDefinitionModel).where(
            SkillDefinitionModel.skill_id == skill_id,
            SkillDefinitionModel.version == version,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError(f"Skill '{skill_id}' v{version} already exists")

    defn = SkillDefinitionModel(
        id=str(uuid4()),
        skill_id=skill_id,
        version=version,
        display_name=data["display_name"],
        description=data.get("description", ""),
        skill_type=data.get("skill_type", "ai"),
        domain=data.get("domain", "general"),
        instructions=data.get("instructions", ""),
        required_models=data.get("required_models", []),
        input_schema=data.get("input_schema", {}),
        output_format=data.get("output_format", {}),
        execution_handler=data.get("execution_handler", ""),
        error_handling=data.get("error_handling", {}),
        created_by=created_by,
        updated_by=created_by,
    )
    db.add(defn)

    state = SkillStateModel(
        id=str(uuid4()),
        skill_id=skill_id,
        version=version,
        is_enabled=data.get("is_enabled", True),
        skill_type=data.get("skill_type", "ai"),
        domain=data.get("domain", "general"),
        updated_by=created_by,
    )
    db.add(state)
    await db.commit()

    return _map_db_skill(defn, state)


async def update_skill_db(
    db: AsyncSession,
    skill_id: str,
    data: dict[str, Any],
    updated_by: str,
) -> SkillDefinition | None:
    """Update an existing skill. Creates a new version if structural changes."""
    result = await db.execute(
        select(SkillDefinitionModel).where(SkillDefinitionModel.skill_id == skill_id)
    )
    existing = result.scalars().all()
    if not existing:
        return None

    # Get the latest version
    latest = _latest_definitions(existing)[0]

    # Determine if we need a new version (structural change) or update in place
    structural_fields = {"input_schema", "output_format", "execution_handler", "skill_type", "domain"}
    is_structural = any(k in data for k in structural_fields)

    if is_structural:
        # Bump version
        current_parts = latest.version.split(".")
        current_parts[-1] = str(int(current_parts[-1]) + 1)
        new_version = ".".join(current_parts)

        new_defn = SkillDefinitionModel(
            id=str(uuid4()),
            skill_id=skill_id,
            version=new_version,
            display_name=data.get("display_name", latest.display_name),
            description=data.get("description", latest.description),
            skill_type=data.get("skill_type", getattr(latest, "skill_type", "ai")),
            domain=data.get("domain", getattr(latest, "domain", "general")),
            instructions=data.get("instructions", getattr(latest, "instructions", "")),
            required_models=data.get("required_models", latest.required_models),
            input_schema=data.get("input_schema", latest.input_schema),
            output_format=data.get("output_format", latest.output_format),
            execution_handler=data.get("execution_handler", latest.execution_handler),
            error_handling=data.get("error_handling", latest.error_handling),
            created_by=updated_by,
            updated_by=updated_by,
        )
        db.add(new_defn)

        # Copy state to new version
        state_result = await db.execute(
            select(SkillStateModel).where(
                SkillStateModel.skill_id == skill_id,
                SkillStateModel.version == latest.version,
            )
        )
        existing_state = state_result.scalar_one_or_none()
        new_state = SkillStateModel(
            id=str(uuid4()),
            skill_id=skill_id,
            version=new_version,
            is_enabled=existing_state.is_enabled if existing_state else True,
            skill_type=data.get("skill_type", getattr(latest, "skill_type", "ai")),
            domain=data.get("domain", getattr(latest, "domain", "general")),
            updated_by=updated_by,
        )
        db.add(new_state)
    else:
        # Update in place
        if "display_name" in data:
            latest.display_name = data["display_name"]
        if "description" in data:
            latest.description = data["description"]
        if "instructions" in data:
            latest.instructions = data["instructions"]
        if "required_models" in data:
            latest.required_models = data["required_models"]
        if "error_handling" in data:
            latest.error_handling = data["error_handling"]
        latest.updated_by = updated_by

        new_defn = latest
        new_state = None

    if "is_enabled" in data:
        state_result = await db.execute(
            select(SkillStateModel).where(
                SkillStateModel.skill_id == skill_id,
                SkillStateModel.version == latest.version,
            )
        )
        st = state_result.scalar_one_or_none()
        if st:
            st.is_enabled = data["is_enabled"]
            st.updated_by = updated_by
        new_state = st

    await db.commit()
    return await get_skill_db(db, skill_id)


async def delete_skill_db(db: AsyncSession, skill_id: str, deleted_by: str) -> bool:
    """Delete a skill and all its versions from the database."""
    result = await db.execute(
        select(SkillDefinitionModel).where(SkillDefinitionModel.skill_id == skill_id)
    )
    defs = result.scalars().all()
    if not defs:
        return False

    for defn in defs:
        await db.delete(defn)

    state_result = await db.execute(
        select(SkillStateModel).where(SkillStateModel.skill_id == skill_id)
    )
    for state in state_result.scalars().all():
        await db.delete(state)

    # Also remove assignments
    assign_result = await db.execute(
        select(SkillAssignmentModel).where(SkillAssignmentModel.skill_id == skill_id)
    )
    for assign in assign_result.scalars().all():
        await db.delete(assign)

    await db.commit()
    return True


async def get_skill_assignment_count(db: AsyncSession, skill_id: str) -> int:
    """Get the number of active assignments for a skill."""
    result = await db.execute(
        select(func.count()).where(
            SkillAssignmentModel.skill_id == skill_id,
            SkillAssignmentModel.is_active == True,
        )
    )
    return result.scalar() or 0


async def list_skills_paginated(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: str = "",
    skill_type: str = "",
    domain: str = "",
    include_disabled: bool = True,
) -> tuple[list[SkillDefinition], int, int]:
    """List skills with pagination, search, and filters."""
    all_skills = await list_skills_db(db, include_disabled=include_disabled)

    # Apply search filter
    if search:
        search_lower = search.lower()
        all_skills = [
            s for s in all_skills
            if search_lower in s.skill_id.lower()
            or search_lower in s.display_name.lower()
            or search_lower in s.description.lower()
            or search_lower in s.domain.lower()
        ]

    # Apply type filter
    if skill_type:
        all_skills = [s for s in all_skills if s.skill_type == skill_type]

    # Apply domain filter
    if domain:
        all_skills = [s for s in all_skills if s.domain == domain]

    total = len(all_skills)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = start + page_size

    return all_skills[start:end], total, total_pages
