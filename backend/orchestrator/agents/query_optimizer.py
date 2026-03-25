"""Query Optimizer Agent — optimizes SQL queries for Snowflake performance."""

from __future__ import annotations

import logging
import re

from ..base_agent import AgentResult, BaseAgent
from ..state import PipelineState

logger = logging.getLogger(__name__)


class QueryOptimizerAgent(BaseAgent):
    """Optimizes SQL queries for Snowflake performance.

    Reads SQL from sql_writer and applies optimization patterns:
    - Sargable predicates
    - CTE restructuring
    - Join order optimization hints
    - Clustering key recommendations
    - LIMIT enforcement
    """

    @property
    def name(self) -> str:
        return "query_optimizer"

    @property
    def dependencies(self) -> list[str]:
        return ["sql_writer"]

    async def run(self, state: PipelineState) -> AgentResult:
        """Optimize SQL queries from the SQL writer.

        Reads queries from sql_writer output, applies optimization patterns,
        and returns optimized queries with recommendations.
        """
        sql_output = state.outputs.get("sql_writer")
        if not sql_output:
            return AgentResult(
                success=False,
                errors=["No SQL queries available from sql_writer"],
            )

        queries = sql_output.get("queries", [])
        if not queries:
            return AgentResult(
                success=False,
                errors=["SQL writer produced no queries"],
            )

        optimized_queries = []
        recommendations = []

        for query in queries:
            optimized, recs = self._optimize_query(query)
            optimized_queries.append(optimized)
            recommendations.extend(recs)

        result = {
            "original_queries": queries,
            "optimized_queries": optimized_queries,
            "recommendations": recommendations,
            "optimization_count": len(recommendations),
            "clustering_suggestions": self._suggest_clustering(queries),
            "warehouse_recommendation": self._suggest_warehouse(queries),
        }

        state.update_state(self.name, "outputs", result)
        return AgentResult(success=True, output=result)

    def _optimize_query(self, query: str) -> tuple[str, list[str]]:
        """Optimize a single SQL query.

        Returns:
            Tuple of (optimized_query, list_of_recommendations).
        """
        recommendations = []
        optimized = query

        # 1. Check for SELECT * and warn
        if re.search(r'SELECT\s+\*', optimized, re.IGNORECASE):
            recommendations.append(
                "Consider selecting specific columns instead of SELECT * "
                "to reduce data transfer and improve performance"
            )

        # 2. Check for non-sargable predicates (functions on indexed columns)
        if re.search(r'WHERE\s+\w+\(.*?\)\s*=', optimized, re.IGNORECASE):
            recommendations.append(
                "Non-sargable predicate detected. Avoid functions on columns in WHERE clause. "
                "Use range comparisons instead (e.g., date_col >= '2024-01-01' instead of YEAR(date_col) = 2024)"
            )

        # 3. Check for missing LIMIT on SELECT without aggregation
        has_limit = bool(re.search(r'LIMIT\s+\d+', optimized, re.IGNORECASE))
        has_agg = bool(re.search(r'(COUNT|SUM|AVG|MAX|MIN)\s*\(', optimized, re.IGNORECASE))
        is_select = bool(re.search(r'^\s*SELECT', optimized, re.IGNORECASE))
        if is_select and not has_limit and not has_agg:
            optimized = optimized.rstrip().rstrip(";") + "\nLIMIT 1000;"
            recommendations.append(
                "Added LIMIT 1000 to prevent unbounded result sets"
            )

        # 4. Check for correlated subqueries
        if re.search(r'SELECT.*\(SELECT.*FROM.*WHERE.*\)', optimized, re.IGNORECASE | re.DOTALL):
            recommendations.append(
                "Correlated subquery detected. Consider rewriting as a JOIN or CTE for better performance"
            )

        # 5. Suggest QUALIFY for window function filtering
        if re.search(r'OVER\s*\(.*?\).*WHERE.*ROW_NUMBER|RANK|DENSE_RANK', optimized, re.IGNORECASE | re.DOTALL):
            recommendations.append(
                "Consider using QUALIFY clause instead of wrapping window functions in a subquery"
            )

        # 6. Suggest using CTEs for complex queries
        nesting_depth = query.count('(') - query.count('SELECT')
        if nesting_depth > 2:
            recommendations.append(
                "Deeply nested subqueries detected. Consider refactoring with CTEs (WITH clauses) for readability"
            )

        return optimized, recommendations

    def _suggest_clustering(self, queries: list[str]) -> list[str]:
        """Suggest clustering keys for large tables referenced in queries."""
        tables = self._extract_tables(queries)
        suggestions = []
        for table in tables:
            if 'fct_' in table or 'fact' in table:
                suggestions.append(f"Consider CLUSTER BY (date_sk) on {table}")
            elif len(table) > 10:
                suggestions.append(f"Consider CLUSTER BY on frequently filtered columns in {table}")
        return suggestions

    def _suggest_warehouse(self, queries: list[str]) -> str:
        """Suggest appropriate warehouse based on query complexity."""
        full_query = " ".join(queries)
        complexity_indicators = [
            len(re.findall(r'JOIN', full_query, re.IGNORECASE)),
            len(re.findall(r'GROUP BY', full_query, re.IGNORECASE)),
            len(re.findall(r'ORDER BY', full_query, re.IGNORECASE)),
            len(re.findall(r'SUBQUERY|SELECT.*SELECT', full_query, re.IGNORECASE | re.DOTALL)),
        ]
        complexity_score = sum(complexity_indicators)

        if complexity_score > 5:
            return "TRANSFORM_WH (XSMALL or larger recommended for complex queries)"
        return "COMPUTE_WH (XSMALL sufficient for simple queries)"

    def _extract_tables(self, queries: list[str]) -> list[str]:
        """Extract table names from SQL queries."""
        tables = set()
        for query in queries:
            matches = re.findall(r'(?:FROM|JOIN|INTO|UPDATE)\s+(\w+)', query, re.IGNORECASE)
            tables.update(matches)
        return sorted(tables)

    def validate_output(self, result: AgentResult) -> bool:
        """Validate that optimization was performed."""
        if not result.success or not result.output:
            return False
        optimized = result.output.get("optimized_queries", [])
        return len(optimized) > 0
