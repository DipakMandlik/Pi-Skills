from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from backend.v2.config import load_settings
from backend.v2.database.client import init_engine, create_tables


async def run_migrations():
    settings = load_settings()
    print(f"Running migrations against: {settings.database_url}")
    init_engine(settings)
    await create_tables()
    print("Migrations complete.")


if __name__ == "__main__":
    asyncio.run(run_migrations())
