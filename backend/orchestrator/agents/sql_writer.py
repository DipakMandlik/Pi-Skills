"""SQL Writer Agent — generates SQL queries from data model designs."""

from __future__ import annotations

import logging

from ..base_agent import AgentResult, BaseAgent
from ..state import PipelineState

logger = logging.getLogger(__name__)


class SQLWriterAgent(BaseAgent):
    """Generates SQL queries based on data model designs and user intent.

    Reads the data architect's output and user intent to produce
    well-formatted, correct SQL queries.
    """

    @property
    def name(self) -> str:
        return "sql_writer"

    @property
    def dependencies(self) -> list[str]:
        return ["data_architect"]

    async def run(self, state: PipelineState) -> AgentResult:
        """Generate SQL queries from the data model design.

        Reads outputs from data_architect and user intent,
        produces SQL queries appropriate for the user's request.
        """
        design = state.outputs.get("data_architect")
        if not design:
            return AgentResult(
                success=False,
                errors=["No data model design available from data_architect"],
            )

        user_intent = state.user_intent
        prompt = user_intent.get("prompt", "")
        entities = design.get("entities", [])
        relationships = design.get("relationships", [])

        # Generate SQL based on intent and design
        queries = self._generate_queries(prompt, entities, relationships)

        result = {
            "queries": queries,
            "dialect": "snowflake",
            "formatting": "uppercase_keywords_with_indentation",
            "uses_ctes": any("WITH" in q for q in queries),
            "uses_window_functions": any("OVER" in q.upper() for q in queries),
            "table_references": self._extract_tables(queries),
        }

        state.update_state(self.name, "outputs", result)
        return AgentResult(success=True, output=result)

    def _generate_queries(
        self,
        prompt: str,
        entities: list[dict],
        relationships: list[dict],
    ) -> list[str]:
        """Generate SQL queries based on prompt and design."""
        prompt_lower = prompt.lower()
        queries = []

        # Determine query type from intent
        if any(kw in prompt_lower for kw in ["create table", "DDL", "schema", "design"]):
            queries = self._generate_ddl_queries(entities)
        elif any(kw in prompt_lower for kw in ["select", "query", "retrieve", "get", "list"]):
            queries = self._generate_select_queries(entities, relationships, prompt)
        elif any(kw in prompt_lower for kw in ["insert", "load", "ingest"]):
            queries = self._generate_insert_queries(entities)
        elif any(kw in prompt_lower for kw in ["update", "modify", "change"]):
            queries = self._generate_update_queries(entities, prompt)
        elif any(kw in prompt_lower for kw in ["join", "combine", "merge"]):
            queries = self._generate_join_queries(entities, relationships)
        else:
            # Default: generate a SELECT query for the primary entity
            if entities:
                primary = entities[0]
                entity_name = primary.get("name", "table_name")
                queries = [f"SELECT * FROM {entity_name} LIMIT 100;"]

        return queries

    def _generate_ddl_queries(self, entities: list[dict]) -> list[str]:
        """Generate DDL queries for entities."""
        queries = []
        for entity in entities:
            name = entity.get("name", "unknown_table")
            entity_type = entity.get("type", "table")

            if entity_type == "dimension":
                queries.append(
                    f"CREATE OR REPLACE TABLE {name} (\n"
                    f"    {name.replace('dim_', '')}_sk NUMBER NOT NULL AUTOINCREMENT PRIMARY KEY,\n"
                    f"    dw_created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),\n"
                    f"    dw_updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP()\n"
                    f");"
                )
            elif entity_type == "fact":
                queries.append(
                    f"CREATE OR REPLACE TABLE {name} (\n"
                    f"    {name.replace('fct_', '')}_sk NUMBER NOT NULL AUTOINCREMENT PRIMARY KEY,\n"
                    f"    etl_loaded_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP()\n"
                    f");"
                )
            else:
                queries.append(f"CREATE OR REPLACE TABLE {name} (id NUMBER PRIMARY KEY);")

        return queries

    def _generate_select_queries(
        self,
        entities: list[dict],
        relationships: list[dict],
        prompt: str,
    ) -> list[str]:
        """Generate SELECT queries based on intent."""
        if not entities:
            return ["SELECT 1;"]

        primary = entities[0]
        entity_name = primary.get("name", "table_name")

        # Check for aggregation intent
        prompt_lower = prompt.lower()
        if any(kw in prompt_lower for kw in ["count", "total", "sum", "aggregate", "group"]):
            return [
                f"SELECT\n"
                f"    COUNT(*) AS total_count,\n"
                f"    COUNT(DISTINCT id) AS unique_count\n"
                f"FROM {entity_name};"
            ]

        # Check for ordering intent
        if any(kw in prompt_lower for kw in ["order", "sort", "latest", "recent", "top"]):
            return [
                f"SELECT *\n"
                f"FROM {entity_name}\n"
                f"ORDER BY dw_created_at DESC\n"
                f"LIMIT 100;"
            ]

        # Default SELECT
        return [f"SELECT *\nFROM {entity_name}\nLIMIT 100;"]

    def _generate_insert_queries(self, entities: list[dict]) -> list[str]:
        """Generate INSERT queries."""
        queries = []
        for entity in entities:
            name = entity.get("name", "table_name")
            queries.append(
                f"INSERT INTO {name} (id, dw_created_at)\n"
                f"VALUES (1, CURRENT_TIMESTAMP());"
            )
        return queries

    def _generate_update_queries(self, entities: list[dict], prompt: str) -> list[str]:
        """Generate UPDATE queries."""
        if not entities:
            return ["SELECT 1;"]

        name = entities[0].get("name", "table_name")
        return [
            f"UPDATE {name}\n"
            f"SET dw_updated_at = CURRENT_TIMESTAMP()\n"
            f"WHERE id = 1;"
        ]

    def _generate_join_queries(
        self,
        entities: list[dict],
        relationships: list[dict],
    ) -> list[str]:
        """Generate JOIN queries based on relationships."""
        if len(entities) < 2 or not relationships:
            return [f"SELECT * FROM {entities[0]['name']} LIMIT 100;" if entities else ["SELECT 1;"]]

        left = entities[0]["name"]
        right = entities[1]["name"]
        rel = relationships[0] if relationships else {}
        fk = rel.get("fk", "id")

        return [
            f"SELECT\n"
            f"    l.*,\n"
            f"    r.*\n"
            f"FROM {left} l\n"
            f"JOIN {right} r ON l.{fk} = r.{fk}\n"
            f"LIMIT 100;"
        ]

    def _extract_tables(self, queries: list[str]) -> list[str]:
        """Extract table names from SQL queries."""
        import re
        tables = set()
        for query in queries:
            # Match FROM and JOIN clauses
            matches = re.findall(r'(?:FROM|JOIN)\s+(\w+)', query, re.IGNORECASE)
            tables.update(matches)
        return sorted(tables)

    def validate_output(self, result: AgentResult) -> bool:
        """Validate that SQL was generated."""
        if not result.success or not result.output:
            return False
        queries = result.output.get("queries", [])
        return len(queries) > 0 and all(isinstance(q, str) and len(q.strip()) > 0 for q in queries)
