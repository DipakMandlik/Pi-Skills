"""Schema Explorer Agent — discovers Snowflake databases, schemas, and tables."""

from __future__ import annotations

import logging
from typing import Any

from ..base_agent import AgentResult, BaseAgent
from ..state import PipelineState

logger = logging.getLogger(__name__)


class SchemaExplorerAgent(BaseAgent):
    """Explores Snowflake metadata to discover databases, schemas, and tables.

    Reads the user's intent and determines which databases/schemas are relevant.
    In production, this connects to Snowflake via the MCP bridge or Snowflake client.
    In development, it uses cached metadata if available.
    """

    @property
    def name(self) -> str:
        return "schema_explorer"

    @property
    def dependencies(self) -> list[str]:
        return ["intent_analyzer"]

    async def run(self, state: PipelineState) -> AgentResult:
        """Explore Snowflake schema based on user intent.

        Reads intent analysis from state, determines relevant databases/schemas,
        and outputs a structured schema inventory.
        """
        intent_output = state.outputs.get("intent_analyzer")
        if not intent_output:
            return AgentResult(
                success=False,
                errors=["No intent analysis available from intent_analyzer"],
            )

        # Determine which databases to explore based on skills
        skills = intent_output.get("all_skills", [])
        execution_path = intent_output.get("execution_path", "simple_query")

        databases_to_explore = self._determine_databases(skills, execution_path)

        # Build schema inventory
        schema_inventory = {
            "databases": databases_to_explore,
            "exploration_strategy": self._get_strategy(execution_path),
            "relevant_schemas": [],
            "relevant_tables": [],
            "metadata_source": "orchestrator_default",
        }

        # In production, this would call the Snowflake client:
        # schema_inventory = await self._explore_snowflake(databases_to_explore)

        state.update_state(self.name, "outputs", schema_inventory)
        state.update_state(self.name, "snowflake_metadata", schema_inventory)

        return AgentResult(success=True, output=schema_inventory)

    def _determine_databases(self, skills: list[str], execution_path: str) -> list[dict[str, Any]]:
        """Determine which databases are relevant based on skills."""
        db_map = {
            "data-architect": [
                {"name": "RAW_DB", "purpose": "Source data exploration"},
                {"name": "CURATED_DB", "purpose": "Business-ready tables"},
                {"name": "STAGING_DB", "purpose": "Transformation layer"},
            ],
            "sql-writer": [
                {"name": "CURATED_DB", "purpose": "Query target tables"},
            ],
            "query-optimizer": [
                {"name": "CURATED_DB", "purpose": "Tables to optimize queries against"},
            ],
            "analytics-engineer": [
                {"name": "CURATED_DB", "purpose": "Analytics source tables"},
                {"name": "PUBLISHED_DB", "purpose": "Published views"},
            ],
            "stored-procedure-writer": [
                {"name": "STAGING_DB", "purpose": "ETL target tables"},
                {"name": "RAW_DB", "purpose": "ETL source tables"},
            ],
            "data-quality-engineer": [
                {"name": "RAW_DB", "purpose": "Source data quality checks"},
                {"name": "CURATED_DB", "purpose": "Curated data quality checks"},
            ],
        }

        databases = []
        seen = set()
        for skill in skills:
            for db in db_map.get(skill, []):
                if db["name"] not in seen:
                    databases.append(db)
                    seen.add(db["name"])

        if not databases:
            databases = [{"name": "CURATED_DB", "purpose": "Default exploration target"}]

        return databases

    def _get_strategy(self, execution_path: str) -> str:
        """Get the exploration strategy based on execution path."""
        strategies = {
            "design_and_build": "full_exploration",
            "query_workflow": "targeted_exploration",
            "procedure_workflow": "etl_exploration",
            "analytics_workflow": "analytics_exploration",
            "full_pipeline": "full_exploration",
            "simple_query": "minimal_exploration",
        }
        return strategies.get(execution_path, "minimal_exploration")

    def validate_output(self, result: AgentResult) -> bool:
        """Validate that schema exploration produced useful results."""
        if not result.success or not result.output:
            return False
        databases = result.output.get("databases", [])
        return len(databases) > 0
