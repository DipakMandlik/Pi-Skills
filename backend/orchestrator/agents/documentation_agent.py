"""Documentation Agent — generates comprehensive documentation from pipeline outputs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from ..base_agent import AgentResult, BaseAgent
from ..state import PipelineState

logger = logging.getLogger(__name__)


class DocumentationAgent(BaseAgent):
    """Generates comprehensive documentation from all agent outputs.

    Runs last in the pipeline to produce:
    - Execution summary
    - Data lineage map
    - SQL documentation
    - API contract documentation
    - Architecture notes
    """

    @property
    def name(self) -> str:
        return "documentation_agent"

    @property
    def dependencies(self) -> list[str]:
        return ["validation_agent"]

    async def run(self, state: PipelineState) -> AgentResult:
        """Generate documentation from all agent outputs.

        Reads outputs from all agents and produces structured documentation.
        """
        # Gather all outputs
        intent = state.outputs.get("intent_analyzer", {})
        schema = state.outputs.get("schema_explorer", {})
        model = state.outputs.get("data_architect", {})
        sql = state.outputs.get("sql_writer", {})
        optimizer = state.outputs.get("query_optimizer", {})
        execution = state.outputs.get("execution_agent", {})
        governance = state.outputs.get("governance_agent", {})
        validation = state.outputs.get("validation_agent", {})

        # Build documentation sections
        doc_sections = {
            "executive_summary": self._build_summary(state, validation),
            "intent_analysis": self._document_intent(intent),
            "data_model": self._document_data_model(model),
            "sql_queries": self._document_sql(sql, optimizer),
            "execution_results": self._document_execution(execution),
            "governance_report": self._document_governance(governance),
            "data_lineage": self._build_lineage(state),
            "metadata": self._build_metadata(state),
        }

        result = {
            "documentation": doc_sections,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "run_id": state.run_id,
            "format": "structured_json",
        }

        state.update_state(self.name, "outputs", result)
        return AgentResult(success=True, output=result)

    def _build_summary(self, state: PipelineState, validation: dict) -> str:
        """Build executive summary."""
        summary = state.get_summary()
        validation_status = validation.get("overall_status", "unknown")

        return (
            f"Pipeline Run: {state.run_id}\n"
            f"Project: {state.project_name}\n"
            f"Status: {validation_status}\n"
            f"Agents Completed: {summary.get('completed', 0)}/{summary.get('total_agents', 0)}\n"
            f"Errors: {summary.get('total_errors', 0)}\n"
            f"Checkpoints Passed: {summary.get('checkpoints_passed', 0)}"
        )

    def _document_intent(self, intent: dict) -> dict[str, Any]:
        """Document intent analysis."""
        return {
            "complexity": intent.get("complexity", "unknown"),
            "skills_used": intent.get("all_skills", []),
            "execution_path": intent.get("execution_path", "unknown"),
        }

    def _document_data_model(self, model: dict) -> dict[str, Any]:
        """Document data model design."""
        if not model:
            return {"status": "not_generated"}

        return {
            "paradigm": model.get("paradigm"),
            "entities": model.get("entities", []),
            "relationships": model.get("relationships", []),
            "ddl_statements": model.get("ddl_statements", []),
        }

    def _document_sql(self, sql: dict, optimizer: dict) -> dict[str, Any]:
        """Document SQL queries."""
        if not sql:
            return {"status": "not_generated"}

        return {
            "queries": sql.get("queries", []),
            "optimized_queries": optimizer.get("optimized_queries", sql.get("queries", [])),
            "optimization_recommendations": optimizer.get("recommendations", []),
            "dialect": sql.get("dialect", "snowflake"),
        }

    def _document_execution(self, execution: dict) -> dict[str, Any]:
        """Document execution results."""
        if not execution:
            return {"status": "not_executed"}

        return {
            "queries_executed": execution.get("queries_executed", 0),
            "all_succeeded": execution.get("all_succeeded", False),
            "total_execution_time_ms": execution.get("total_execution_time_ms", 0),
            "failed_queries": execution.get("failed_queries", []),
        }

    def _document_governance(self, governance: dict) -> dict[str, Any]:
        """Document governance report."""
        if not governance:
            return {"status": "not_analyzed"}

        return {
            "compliance": governance.get("compliance", {}),
            "cost_analysis": governance.get("cost_analysis", {}),
            "security_checks": governance.get("security_checks", {}),
            "recommendations": governance.get("recommendations", []),
        }

    def _build_lineage(self, state: PipelineState) -> list[dict[str, str]]:
        """Build data lineage map from agent outputs."""
        lineage = []

        # Source → Intent Analysis
        lineage.append({
            "source": "user_input",
            "transformation": "intent_analysis",
            "target": "structured_intent",
        })

        # Intent → Schema Exploration
        lineage.append({
            "source": "structured_intent",
            "transformation": "schema_exploration",
            "target": "schema_inventory",
        })

        # Schema → Data Model
        lineage.append({
            "source": "schema_inventory",
            "transformation": "data_model_design",
            "target": "data_model",
        })

        # Model → SQL
        lineage.append({
            "source": "data_model",
            "transformation": "sql_generation",
            "target": "sql_queries",
        })

        # SQL → Optimized SQL
        lineage.append({
            "source": "sql_queries",
            "transformation": "query_optimization",
            "target": "optimized_queries",
        })

        # Optimized SQL → Execution
        lineage.append({
            "source": "optimized_queries",
            "transformation": "execution",
            "target": "execution_results",
        })

        # Execution → Governance
        lineage.append({
            "source": "execution_results",
            "transformation": "governance_analysis",
            "target": "governance_report",
        })

        return lineage

    def _build_metadata(self, state: PipelineState) -> dict[str, Any]:
        """Build pipeline metadata."""
        return {
            "run_id": state.run_id,
            "project_name": state.project_name,
            "started_at": state.started_at.isoformat(),
            "completed_at": state.last_updated.isoformat(),
            "version": state.version,
            "total_agents": len(state.task_status),
            "agent_statuses": dict(state.task_status),
            "error_count": len(state.errors_log),
            "validation_results": state.validation_results,
        }

    def validate_output(self, result: AgentResult) -> bool:
        """Validate that documentation was generated."""
        if not result.success or not result.output:
            return False
        doc = result.output.get("documentation", {})
        return "metadata" in doc and "executive_summary" in doc
