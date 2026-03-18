from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from .config import Settings
from .security import (
    ValidationError,
    apply_row_limit,
    enforce_safety,
    validate_days,
    validate_identifier,
    validate_max_rows,
)
from .snowflake_client import SnowflakeClient

ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]


class ToolRegistry:
    def __init__(self, settings: Settings, sf: SnowflakeClient) -> None:
        self.settings = settings
        self.sf = sf
        self._tools: dict[str, tuple[ToolDefinition, ToolHandler]] = {}
        self._register_tools()

    def list_tools(self) -> list[ToolDefinition]:
        return [tool for tool, _ in self._tools.values()]

    def run_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        entry = self._tools.get(name)
        if not entry:
            raise ValidationError(f"Unknown tool: {name}")
        _, handler = entry
        return handler(arguments)

    def _register(self, definition: ToolDefinition, handler: ToolHandler) -> None:
        self._tools[definition.name] = (definition, handler)

    def _register_tools(self) -> None:
        self._register(
            ToolDefinition(
                name="run_query",
                description="Execute a Snowflake SQL query with safety checks and row limits.",
                input_schema={
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {"type": "string", "minLength": 1},
                        "max_rows": {"type": "integer", "minimum": 1},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "query_id": {"type": "string"},
                        "executed_query": {"type": "string"},
                        "columns": {"type": "array", "items": {"type": "string"}},
                        "rows": {"type": "array", "items": {"type": "array"}},
                        "row_count": {"type": "integer"},
                    },
                },
            ),
            self._run_query,
        )

        self._register(
            ToolDefinition(
                name="list_databases",
                description="List databases visible to the configured Snowflake role.",
                input_schema={"type": "object", "properties": {}},
                output_schema={
                    "type": "object",
                    "properties": {
                        "databases": {"type": "array", "items": {"type": "string"}},
                        "query_id": {"type": "string"},
                    },
                },
            ),
            self._list_databases,
        )

        self._register(
            ToolDefinition(
                name="list_schemas",
                description="List schemas in a given database.",
                input_schema={
                    "type": "object",
                    "required": ["database"],
                    "properties": {"database": {"type": "string", "minLength": 1}},
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "schemas": {"type": "array", "items": {"type": "string"}},
                        "query_id": {"type": "string"},
                    },
                },
            ),
            self._list_schemas,
        )

        self._register(
            ToolDefinition(
                name="list_tables",
                description="List tables in a given database schema.",
                input_schema={
                    "type": "object",
                    "required": ["database", "schema"],
                    "properties": {
                        "database": {"type": "string", "minLength": 1},
                        "schema": {"type": "string", "minLength": 1},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "tables": {"type": "array", "items": {"type": "string"}},
                        "query_id": {"type": "string"},
                    },
                },
            ),
            self._list_tables,
        )

        self._register(
            ToolDefinition(
                name="describe_table",
                description="Describe columns and metadata for a Snowflake table.",
                input_schema={
                    "type": "object",
                    "required": ["database", "schema", "table"],
                    "properties": {
                        "database": {"type": "string", "minLength": 1},
                        "schema": {"type": "string", "minLength": 1},
                        "table": {"type": "string", "minLength": 1},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "columns": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "type": {"type": "string"},
                                    "nullable": {"type": "string"},
                                    "default": {"type": ["string", "null"]},
                                },
                            },
                        },
                        "query_id": {"type": "string"},
                    },
                },
            ),
            self._describe_table,
        )

        self._register(
            ToolDefinition(
                name="list_warehouses",
                description="List Snowflake virtual warehouses.",
                input_schema={"type": "object", "properties": {}},
                output_schema={
                    "type": "object",
                    "properties": {
                        "warehouses": {"type": "array", "items": {"type": "string"}},
                        "query_id": {"type": "string"},
                    },
                },
            ),
            self._list_warehouses,
        )

        self._register(
            ToolDefinition(
                name="warehouse_usage",
                description="Summarize warehouse usage over the last N days using ACCOUNT_USAGE views.",
                input_schema={
                    "type": "object",
                    "required": ["warehouse", "days"],
                    "properties": {
                        "warehouse": {"type": "string", "minLength": 1},
                        "days": {"type": "integer", "minimum": 1, "maximum": 90},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "warehouse": {"type": "string"},
                        "days": {"type": "integer"},
                        "credits_used": {"type": "number"},
                        "avg_running": {"type": "number"},
                        "query_id": {"type": "string"},
                    },
                },
            ),
            self._warehouse_usage,
        )

    def _run_query(self, args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", "")).strip()
        if not query:
            raise ValidationError("query is required")

        enforce_safety(query, self.settings.sql_safety_mode)
        requested_max_rows = validate_max_rows(args.get("max_rows"), self.settings.sql_max_rows)
        limited_query = apply_row_limit(query, min(requested_max_rows, self.settings.sql_default_row_limit))
        result = self.sf.execute_query(limited_query)
        result["executed_query"] = limited_query
        return result

    def _list_databases(self, _args: dict[str, Any]) -> dict[str, Any]:
        return self.sf.execute_list(
            "SHOW DATABASES",
            "databases",
            value_column_candidates=["name", "database_name"],
        )

    def _list_schemas(self, args: dict[str, Any]) -> dict[str, Any]:
        database = validate_identifier(str(args.get("database", "")), "database")
        return self.sf.execute_list(
            f"SHOW SCHEMAS IN DATABASE {database}",
            "schemas",
            value_column_candidates=["name", "schema_name"],
        )

    def _list_tables(self, args: dict[str, Any]) -> dict[str, Any]:
        database = validate_identifier(str(args.get("database", "")), "database")
        schema = validate_identifier(str(args.get("schema", "")), "schema")
        return self.sf.execute_list(
            f"SHOW TABLES IN SCHEMA {database}.{schema}",
            "tables",
            value_column_candidates=["name", "table_name"],
        )

    def _describe_table(self, args: dict[str, Any]) -> dict[str, Any]:
        database = validate_identifier(str(args.get("database", "")), "database")
        schema = validate_identifier(str(args.get("schema", "")), "schema")
        table = validate_identifier(str(args.get("table", "")), "table")
        result = self.sf.execute_query(f"DESC TABLE {database}.{schema}.{table}")

        columns: list[dict[str, Any]] = []
        for row in result["rows"]:
            columns.append(
                {
                    "name": row[0] if len(row) > 0 else None,
                    "type": row[1] if len(row) > 1 else None,
                    "nullable": row[3] if len(row) > 3 else None,
                    "default": row[4] if len(row) > 4 else None,
                }
            )

        return {"columns": columns, "query_id": result["query_id"]}

    def _list_warehouses(self, _args: dict[str, Any]) -> dict[str, Any]:
        return self.sf.execute_list(
            "SHOW WAREHOUSES",
            "warehouses",
            value_column_candidates=["name", "warehouse_name"],
        )

    def _warehouse_usage(self, args: dict[str, Any]) -> dict[str, Any]:
        warehouse = validate_identifier(str(args.get("warehouse", "")), "warehouse")
        days = validate_days(int(args.get("days", 0)))

        start_ts = datetime.now(timezone.utc) - timedelta(days=days)
        query = f"""
            SELECT
                WAREHOUSE_NAME,
                COALESCE(SUM(AVG_RUNNING), 0) AS TOTAL_AVG_RUNNING,
                COALESCE(SUM(CREDITS_USED), 0) AS TOTAL_CREDITS_USED
            FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_LOAD_HISTORY
            WHERE WAREHOUSE_NAME = '{warehouse.upper()}'
              AND START_TIME >= '{start_ts.strftime('%Y-%m-%d %H:%M:%S')}'
            GROUP BY WAREHOUSE_NAME
        """.strip()

        result = self.sf.execute_query(query)
        if not result["rows"]:
            return {
                "warehouse": warehouse,
                "days": days,
                "credits_used": 0,
                "avg_running": 0,
                "query_id": result["query_id"],
            }

        row = result["rows"][0]
        return {
            "warehouse": warehouse,
            "days": days,
            "credits_used": float(row[2] or 0),
            "avg_running": float(row[1] or 0),
            "query_id": result["query_id"],
        }
