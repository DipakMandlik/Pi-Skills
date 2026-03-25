"""Execution Agent — executes SQL queries via the MCP bridge / Snowflake client."""

from __future__ import annotations

import logging
import time
from typing import Any

from ..base_agent import AgentResult, BaseAgent
from ..state import PipelineState

logger = logging.getLogger(__name__)


class ExecutionAgent(BaseAgent):
    """Executes SQL queries against Snowflake via the MCP bridge or Snowflake client.

    Reads optimized SQL from query_optimizer (or queries from sql_writer),
    executes them, and captures results, timing, and metadata.
    """

    @property
    def name(self) -> str:
        return "execution_agent"

    @property
    def dependencies(self) -> list[str]:
        return ["query_optimizer"]

    async def run(self, state: PipelineState) -> AgentResult:
        """Execute SQL queries and capture results.

        Reads optimized queries from query_optimizer output,
        executes them, and returns execution results.
        """
        optimizer_output = state.outputs.get("query_optimizer")
        sql_output = state.outputs.get("sql_writer")

        if optimizer_output and "optimized_queries" in optimizer_output:
            queries = optimizer_output["optimized_queries"]
        elif sql_output and "queries" in sql_output:
            queries = sql_output["queries"]
        else:
            return AgentResult(
                success=False,
                errors=["No queries available from sql_writer or query_optimizer"],
            )

        if not queries:
            return AgentResult(
                success=False,
                errors=["No queries to execute"],
            )

        # Execute each query
        execution_results = []
        total_tokens = 0
        total_cost = 0.0

        for query in queries:
            result = await self._execute_query(query)
            execution_results.append(result)

            # Track token usage (estimated)
            estimated_tokens = len(query.split()) * 1.3
            total_tokens += int(estimated_tokens)

        result = {
            "queries_executed": len(queries),
            "results": execution_results,
            "all_succeeded": all(r["success"] for r in execution_results),
            "failed_queries": [
                r["query"] for r in execution_results if not r["success"]
            ],
            "estimated_tokens_used": total_tokens,
            "total_execution_time_ms": sum(r["execution_time_ms"] for r in execution_results),
        }

        # Update governance tracking
        state.update_state(self.name, "token_usage", {"execution_agent": total_tokens})

        state.update_state(self.name, "outputs", result)
        return AgentResult(success=True, output=result)

    async def _execute_query(self, query: str) -> dict[str, Any]:
        """Execute a single query.

        In production, this connects to Snowflake via the MCP bridge or
        Snowflake client. For now, it simulates execution with validation.
        """
        start_time = time.time()

        try:
            # Validate query syntax (basic check)
            validation = self._validate_query_syntax(query)
            if not validation["valid"]:
                return {
                    "query": query,
                    "success": False,
                    "error": validation["error"],
                    "execution_time_ms": 0,
                    "rows_affected": 0,
                }

            # In production, this would be:
            # result = await snowflake_client.execute(query)
            # For now, simulate successful execution
            execution_time_ms = (time.time() - start_time) * 1000

            return {
                "query": query,
                "success": True,
                "execution_time_ms": round(execution_time_ms, 2),
                "rows_affected": 0,  # Would come from Snowflake
                "result_preview": "Query executed successfully (simulated)",
            }

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            return {
                "query": query,
                "success": False,
                "error": str(e),
                "execution_time_ms": round(execution_time_ms, 2),
                "rows_affected": 0,
            }

    def _validate_query_syntax(self, query: str) -> dict[str, Any]:
        """Basic SQL syntax validation."""
        query_stripped = query.strip()

        if not query_stripped:
            return {"valid": False, "error": "Empty query"}

        # Check for basic SQL keywords
        valid_starts = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "WITH", "CALL", "SHOW", "DESCRIBE", "USE", "GRANT", "REVOKE"]
        first_word = query_stripped.split()[0].upper()

        if first_word not in valid_starts:
            return {
                "valid": False,
                "error": f"Query does not start with a valid SQL keyword (found: {first_word})",
            }

        # Check for unbalanced parentheses
        if query_stripped.count("(") != query_stripped.count(")"):
            return {
                "valid": False,
                "error": "Unbalanced parentheses in query",
            }

        return {"valid": True}

    def validate_output(self, result: AgentResult) -> bool:
        """Validate that execution produced results."""
        if not result.success or not result.output:
            return False
        results = result.output.get("results", [])
        return len(results) > 0
