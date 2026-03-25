from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
    func,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import Settings

logger = logging.getLogger("backend.database")


# ── Portable column types ───────────────────────────────────────────

class GUID(TypeDecorator):
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return None

    def process_result_value(self, value, dialect):
        return value


class JSONEncoded(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None and isinstance(value, str):
            return json.loads(value)
        return value


class INETType(TypeDecorator):
    impl = String(45)
    cache_ok = True


# ── Base ────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── Models ──────────────────────────────────────────────────────────

class UserModel(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    external_id = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    display_name = Column(String(255))
    platform_role = Column(String(50), nullable=False, default="user")
    is_active = Column(Boolean, default=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    last_login_at = Column(DateTime)
    metadata_ = Column("metadata", JSONEncoded, default=dict)


class ModelPermissionModel(Base):
    __tablename__ = "model_permissions"
    __table_args__ = (
        UniqueConstraint("user_id", "model_id", name="uq_user_model"),
    )

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(GUID(), nullable=False, index=True)
    model_id = Column(String(255), nullable=False)
    granted_by = Column(GUID(), nullable=False)
    granted_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    revoked_by = Column(GUID())
    revoked_at = Column(DateTime)
    notes = Column(Text)


class SkillAssignmentModel(Base):
    __tablename__ = "skill_assignments"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),
    )

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(GUID(), nullable=False, index=True)
    skill_id = Column(String(255), nullable=False)
    assigned_by = Column(GUID(), nullable=False)
    assigned_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    revoked_by = Column(GUID())
    revoked_at = Column(DateTime)


class RegisteredModelModel(Base):
    __tablename__ = "registered_models"

    model_id = Column(String(255), primary_key=True)
    display_name = Column(String(255), nullable=False)
    provider = Column(String(100), nullable=False)
    tier = Column(String(50), default="standard")
    is_available = Column(Boolean, default=True)
    max_tokens = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())


class AuditLogModel(Base):
    __tablename__ = "audit_log"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    request_id = Column(GUID(), nullable=False)
    user_id = Column(GUID(), index=True)
    skill_id = Column(String(255))
    model_id = Column(String(255))
    action = Column(String(100), nullable=False)
    outcome = Column(String(50), nullable=False)
    tokens_used = Column(Integer)
    latency_ms = Column(Integer)
    ip_address = Column(INETType)
    user_agent = Column(Text)
    error_detail = Column(Text)
    metadata_ = Column("metadata", JSONEncoded, default=dict)
    timestamp = Column(DateTime, server_default=func.now())


# ── Engine + Session ────────────────────────────────────────────────

_engine = None
_session_factory = None


def _get_dsn(settings: Settings) -> str:
    dsn = settings.postgres_dsn
    if "postgresql" in dsn:
        return dsn.replace("postgresql+asyncpg", "postgresql+asyncpg")
    return dsn


def init_engine(settings: Settings):
    global _engine, _session_factory

    dsn = _get_dsn(settings)

    # Auto-detect: if postgresql DSN but no PostgreSQL available, fallback to SQLite
    if "postgresql" in dsn:
        try:
            # Quick test if asyncpg is usable
            import asyncpg  # noqa: F401
        except Exception:
            logger.warning("asyncpg not available, falling back to SQLite")
            dsn = "sqlite+aiosqlite:///./backend_dev.db"

    logger.info("Database engine: %s", dsn.split("@")[-1] if "@" in dsn else dsn)

    _engine = create_async_engine(
        dsn,
        echo=settings.debug,
        pool_pre_ping=True,
    )
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("Database engine not initialised. Call init_engine() first.")
    async with _session_factory() as session:
        yield session


async def create_tables():
    if _engine is None:
        raise RuntimeError("Database engine not initialised. Call init_engine() first.")
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
