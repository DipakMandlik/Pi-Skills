from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from . import database


def _alembic_config_path() -> str:
    return str(Path(__file__).resolve().parents[2] / "alembic.ini")


def _expected_head_revision() -> str:
    cfg = Config(_alembic_config_path())
    script_dir = ScriptDirectory.from_config(cfg)
    heads = script_dir.get_heads()
    if len(heads) != 1:
        raise RuntimeError(
            f"Expected exactly one Alembic head revision, found {len(heads)}: {heads}",
        )
    return heads[0]


async def assert_schema_at_head() -> None:
    if database._engine is None:
        raise RuntimeError("Database engine not initialised")

    expected_head = _expected_head_revision()

    async with database._engine.connect() as conn:
        exists_result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"),
        )
        exists = exists_result.scalar_one_or_none() is not None

        if not exists:
            raise RuntimeError(
                "Database schema is not initialized with Alembic. "
                "Run: py -3.12 -m alembic -c alembic.ini upgrade head",
            )

        version_result = await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        current_version = version_result.scalar_one_or_none()

    if current_version != expected_head:
        raise RuntimeError(
            "Database schema is not at migration head. "
            f"Current={current_version!r}, Expected={expected_head!r}. "
            "Run: py -3.12 -m alembic -c alembic.ini upgrade head",
        )
