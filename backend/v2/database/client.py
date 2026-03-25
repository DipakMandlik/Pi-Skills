from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, TypeDecorator, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.v2.config.settings import Settings

logger = logging.getLogger("backend.v2.database")


class GUID(TypeDecorator):
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return str(value) if value is not None else None

    def process_result_value(self, value, dialect):
        return value


class JSONEncoded(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        import json
        return json.dumps(value) if value is not None else None

    def process_result_value(self, value, dialect):
        import json
        if value is not None and isinstance(value, str):
            return json.loads(value)
        return value


class Base(DeclarativeBase):
    pass


class OrganizationModel(Base):
    __tablename__ = "organizations"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    plan = Column(String(50), nullable=False, default="free")
    settings = Column("settings", JSONEncoded, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class UserModel(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    org_id = Column(GUID(), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="MEMBER")
    status = Column(String(50), nullable=False, default="active")
    password_hash = Column(String(255), nullable=False)
    last_active = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class TeamModel(Base):
    __tablename__ = "teams"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    org_id = Column(GUID(), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class TeamMemberModel(Base):
    __tablename__ = "team_members"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    team_id = Column(GUID(), nullable=False, index=True)
    user_id = Column(GUID(), nullable=False, index=True)
    joined_at = Column(DateTime, server_default=func.now())


class SkillModel(Base):
    __tablename__ = "skills"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    org_id = Column(GUID(), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    content = Column(Text, default="")
    category = Column(String(100), default="general")
    status = Column(String(50), nullable=False, default="draft", index=True)
    created_by = Column(GUID(), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, index=True)

    domain = Column(String(100), default="general")
    required_models = Column("required_models", JSONEncoded, default=list)
    input_schema = Column("input_schema", JSONEncoded, default=dict)
    output_format = Column("output_format", JSONEncoded, default=dict)
    execution_handler = Column(String(255), default="")
    error_handling = Column("error_handling", JSONEncoded, default=dict)
    instructions = Column(Text, default="")


class SkillVersionModel(Base):
    __tablename__ = "skill_versions"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    skill_id = Column(GUID(), nullable=False, index=True)
    content = Column(Text, nullable=False)
    version = Column(Integer, nullable=False)
    created_by = Column(GUID(), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class SkillFileModel(Base):
    __tablename__ = "skill_files"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    skill_id = Column(GUID(), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False)
    storage_path = Column(String(500), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class SkillAssignmentModel(Base):
    __tablename__ = "skill_assignments"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    skill_id = Column(GUID(), nullable=False, index=True)
    assignee_type = Column(String(50), nullable=False, index=True)
    assignee_id = Column(GUID(), nullable=False, index=True)
    assigned_by = Column(GUID(), nullable=False)
    assigned_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)


class SkillExecutionModel(Base):
    __tablename__ = "skill_executions"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    skill_id = Column(GUID(), nullable=False, index=True)
    user_id = Column(GUID(), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending")
    input_data = Column(JSONEncoded)
    output_data = Column(JSONEncoded)
    error = Column(Text)
    duration_ms = Column(Integer)
    created_at = Column(DateTime, server_default=func.now(), index=True)


class InvitationModel(Base):
    __tablename__ = "invitations"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    org_id = Column(GUID(), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="MEMBER")
    token = Column(String(255), unique=True, nullable=False, index=True)
    invited_by = Column(GUID(), nullable=False)
    accepted_at = Column(DateTime)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class AuditLogModel(Base):
    __tablename__ = "audit_log"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    org_id = Column(GUID(), nullable=False, index=True)
    user_id = Column(GUID(), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(GUID())
    metadata_ = Column("metadata", JSONEncoded, default=dict)
    created_at = Column(DateTime, server_default=func.now(), index=True)


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(GUID(), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now())


_engine = None
_session_factory = None


def init_engine(settings: Settings):
    global _engine, _session_factory
    dsn = settings.database_url

    if "postgresql" in dsn:
        logger.info("Initializing PostgreSQL engine")
        _engine = create_async_engine(
            dsn,
            echo=settings.debug,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
        )
    else:
        logger.info("Initializing SQLite engine: %s", dsn)
        _engine = create_async_engine(dsn, echo=settings.debug)

    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    logger.info("Database engine initialized")


async def create_tables():
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call init_engine() first.")
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("All tables created/verified")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("Database engine not initialized. Call init_engine() first.")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
