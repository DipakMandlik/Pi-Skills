from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from backend.core.config import load_settings
from backend.core import database as db_module
from backend.core.database import (
    SkillDefinitionModel,
    SkillStateModel,
    create_tables,
    init_engine,
)
from backend.services.skill_registry import get_default_registry_items

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("backend.migrate_skill_registry")


async def migrate_skill_registry() -> None:
    settings = load_settings()
    init_engine(settings)
    await create_tables()

    if db_module._session_factory is None:
        raise RuntimeError("Session factory was not initialized")

    inserted_definitions = 0
    inserted_states = 0

    async with db_module._session_factory() as db:
        for item in get_default_registry_items():
            def_result = await db.execute(
                select(SkillDefinitionModel).where(
                    SkillDefinitionModel.skill_id == item.skill_id,
                    SkillDefinitionModel.version == item.version,
                )
            )
            if def_result.scalar_one_or_none() is None:
                db.add(
                    SkillDefinitionModel(
                        skill_id=item.skill_id,
                        version=item.version,
                        display_name=item.display_name,
                        description=item.description,
                        required_models=item.required_models,
                        input_schema=item.input_schema,
                        output_format=item.output_format,
                        execution_handler=item.execution_handler,
                        error_handling=item.error_handling,
                        created_by="migration-script",
                        updated_by="migration-script",
                    )
                )
                inserted_definitions += 1

            state_result = await db.execute(
                select(SkillStateModel).where(
                    SkillStateModel.skill_id == item.skill_id,
                    SkillStateModel.version == item.version,
                )
            )
            if state_result.scalar_one_or_none() is None:
                db.add(
                    SkillStateModel(
                        skill_id=item.skill_id,
                        version=item.version,
                        is_enabled=item.is_enabled,
                        updated_by="migration-script",
                    )
                )
                inserted_states += 1

        if inserted_definitions or inserted_states:
            await db.commit()

    logger.info(
        "Skill registry migration complete: inserted_definitions=%s inserted_states=%s",
        inserted_definitions,
        inserted_states,
    )


if __name__ == "__main__":
    asyncio.run(migrate_skill_registry())
