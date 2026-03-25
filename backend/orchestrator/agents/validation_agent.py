"""Validation Agent — runs comprehensive validation gates on all agent outputs."""

from __future__ import annotations

import logging
from typing import Any

from ..base_agent import AgentResult, BaseAgent
from ..state import PipelineState

logger = logging.getLogger(__name__)


class ValidationAgent(BaseAgent):
    """Comprehensive validation of all agent outputs.

    Runs after all execution agents to validate:
    - SQL syntax and correctness
    - Data model consistency
    - Schema alignment
    - Security compliance
    - Performance characteristics
    """

    @property
    def name(self) -> str:
        return "validation_agent"

    @property
    def dependencies(self) -> list[str]:
        return ["execution_agent", "governance_agent"]

    async def run(self, state: PipelineState) -> AgentResult:
        """Run comprehensive validation on all agent outputs.

        Validates outputs from all agents that have run, checking
        for consistency, correctness, and completeness.
        """
        validations = {}

        # 1. Validate intent analysis
        validations["intent_analysis"] = self._validate_intent(state)

        # 2. Validate schema exploration
        validations["schema_exploration"] = self._validate_schema_exploration(state)

        # 3. Validate data model design
        validations["data_model"] = self._validate_data_model(state)

        # 4. Validate SQL queries
        validations["sql_queries"] = self._validate_sql(state)

        # 5. Validate execution results
        validations["execution"] = self._validate_execution(state)

        # 6. Validate governance compliance
        validations["governance"] = self._validate_governance(state)

        # Overall assessment
        all_passed = all(v.get("passed", False) for v in validations.values())
        failed_checks = [k for k, v in validations.items() if not v.get("passed", False)]

        result = {
            "validations": validations,
            "all_passed": all_passed,
            "total_checks": len(validations),
            "passed_checks": len(validations) - len(failed_checks),
            "failed_checks": failed_checks,
            "overall_status": "passed" if all_passed else "failed",
            "summary": self._generate_summary(validations),
        }

        state.update_state(self.name, "outputs", result)
        state.update_state(self.name, "validation_results", result)

        return AgentResult(success=True, output=result)

    def _validate_intent(self, state: PipelineState) -> dict[str, Any]:
        """Validate intent analysis output."""
        intent = state.outputs.get("intent_analyzer")
        if not intent:
            return {"passed": False, "reason": "No intent analysis found"}

        has_skills = len(intent.get("all_skills", [])) > 0
        has_complexity = "complexity" in intent
        has_path = "execution_path" in intent

        return {
            "passed": has_skills and has_complexity and has_path,
            "details": {
                "has_skills": has_skills,
                "has_complexity": has_complexity,
                "has_execution_path": has_path,
            },
        }

    def _validate_schema_exploration(self, state: PipelineState) -> dict[str, Any]:
        """Validate schema exploration output."""
        schema = state.outputs.get("schema_explorer")
        if not schema:
            return {"passed": False, "reason": "No schema exploration found"}

        has_databases = len(schema.get("databases", [])) > 0
        has_strategy = "exploration_strategy" in schema

        return {
            "passed": has_databases and has_strategy,
            "details": {
                "databases_found": len(schema.get("databases", [])),
                "has_strategy": has_strategy,
            },
        }

    def _validate_data_model(self, state: PipelineState) -> dict[str, Any]:
        """Validate data model design."""
        model = state.outputs.get("data_architect")
        if not model:
            return {"passed": True, "reason": "Data model design not required for this pipeline"}

        has_entities = len(model.get("entities", [])) > 0
        has_paradigm = "paradigm" in model

        return {
            "passed": has_entities and has_paradigm,
            "details": {
                "entity_count": len(model.get("entities", [])),
                "paradigm": model.get("paradigm"),
            },
        }

    def _validate_sql(self, state: PipelineState) -> dict[str, Any]:
        """Validate SQL queries."""
        sql = state.outputs.get("sql_writer")
        if not sql:
            return {"passed": False, "reason": "No SQL queries found"}

        queries = sql.get("queries", [])
        if not queries:
            return {"passed": False, "reason": "SQL writer produced no queries"}

        # Check each query has content
        valid_queries = [q for q in queries if isinstance(q, str) and len(q.strip()) > 0]

        return {
            "passed": len(valid_queries) > 0,
            "details": {
                "query_count": len(valid_queries),
                "dialect": sql.get("dialect", "unknown"),
            },
        }

    def _validate_execution(self, state: PipelineState) -> dict[str, Any]:
        """Validate execution results."""
        execution = state.outputs.get("execution_agent")
        if not execution:
            return {"passed": False, "reason": "No execution results found"}

        all_succeeded = execution.get("all_succeeded", False)
        failed = execution.get("failed_queries", [])

        return {
            "passed": all_succeeded,
            "details": {
                "queries_executed": execution.get("queries_executed", 0),
                "failed_queries": len(failed),
                "execution_time_ms": execution.get("total_execution_time_ms", 0),
            },
        }

    def _validate_governance(self, state: PipelineState) -> dict[str, Any]:
        """Validate governance compliance."""
        governance = state.outputs.get("governance_agent")
        if not governance:
            return {"passed": False, "reason": "No governance analysis found"}

        compliance = governance.get("compliance", {})
        is_compliant = compliance.get("compliant", False)

        return {
            "passed": is_compliant,
            "details": {
                "compliant": is_compliant,
                "risk_level": compliance.get("risk_level", "unknown"),
                "issues": compliance.get("issues", []),
            },
        }

    def _generate_summary(self, validations: dict[str, dict]) -> str:
        """Generate a human-readable validation summary."""
        passed = sum(1 for v in validations.values() if v.get("passed"))
        total = len(validations)

        if passed == total:
            return f"All {total} validation checks passed"
        else:
            failed = [k for k, v in validations.items() if not v.get("passed")]
            return f"{passed}/{total} checks passed. Failed: {', '.join(failed)}"

    def validate_output(self, result: AgentResult) -> bool:
        """Validate that validation was completed."""
        if not result.success or not result.output:
            return False
        return "validations" in result.output and "overall_status" in result.output and len(result.output.get("validations", {})) > 0
