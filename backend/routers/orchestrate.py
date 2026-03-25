"""Orchestration router — exposes the multi-agent pipeline as HTTP endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from ..orchestrator.base_agent import AgentResult
from ..orchestrator.config import PipelineConfig
from ..orchestrator.orchestrator import Orchestrator
from ..orchestrator.state import PipelineState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orchestrate", tags=["orchestration"])

# Active pipeline runs (in-memory; use Redis for production)
_active_runs: dict[str, PipelineState] = {}


@router.post("/run")
async def run_pipeline(payload: dict[str, Any]) -> dict[str, Any]:
    """Execute the full multi-agent orchestration pipeline.

    Request body:
    {
        "user_intent": {"prompt": "...", "context": {...}},
        "selected_skills": ["data-architect", "sql-writer"],
        "user_id": "optional-user-id",
        "config": {
            "max_retries": 3,
            "parallel_limit": 3,
            "checkpoint_strict_mode": true
        }
    }

    Returns:
        Pipeline execution results with all agent outputs.
    """
    user_intent = payload.get("user_intent", {})
    selected_skills = payload.get("selected_skills", [])
    user_id = payload.get("user_id")
    config_data = payload.get("config", {})

    if not user_intent and not selected_skills:
        raise HTTPException(
            status_code=400,
            detail="Either user_intent or selected_skills must be provided",
        )

    # Initialize state
    state = PipelineState(
        project_name=user_intent.get("project_name", "AI Governance Pipeline"),
        user_intent=user_intent,
        selected_skills=selected_skills,
        user_id=user_id,
    )

    # Initialize config
    config = PipelineConfig(
        max_retries=config_data.get("max_retries", 3),
        parallel_limit=config_data.get("parallel_limit", 3),
        checkpoint_strict_mode=config_data.get("checkpoint_strict_mode", True),
        log_level=config_data.get("log_level", "INFO"),
    )

    # Register all agents
    from ..orchestrator.agents import (
        DataArchitectAgent,
        DocumentationAgent,
        ExecutionAgent,
        GovernanceAgent,
        IntentAnalyzerAgent,
        ProcedureWriterAgent,
        QueryOptimizerAgent,
        SchemaExplorerAgent,
        SQLWriterAgent,
        ValidationAgent,
    )

    agents = [
        IntentAnalyzerAgent(),
        SchemaExplorerAgent(),
        DataArchitectAgent(),
        SQLWriterAgent(),
        QueryOptimizerAgent(),
        ProcedureWriterAgent(),
        ExecutionAgent(),
        GovernanceAgent(),
        ValidationAgent(),
        DocumentationAgent(),
    ]

    # Create and run orchestrator
    orchestrator = Orchestrator(agents, state, config)

    # Register validation checkpoints
    orchestrator.register_checkpoint("intent_analyzer", "intent_validation")
    orchestrator.register_checkpoint("schema_explorer", "schema_consistency")
    orchestrator.register_checkpoint("sql_writer", "sql_syntax_check")
    orchestrator.register_checkpoint("execution_agent", "execution_validation")
    orchestrator.register_checkpoint("governance_agent", "governance_compliance")

    # Track this run
    _active_runs[state.run_id] = state

    try:
        result = await orchestrator.run()
        return result
    except Exception as e:
        logger.exception("Pipeline execution failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(e)}",
        )


@router.get("/runs/{run_id}")
async def get_run_status(run_id: str) -> dict[str, Any]:
    """Get the status of a pipeline run."""
    state = _active_runs.get(run_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    return {
        "run_id": run_id,
        "status": state.get_summary(),
        "task_status": state.task_status,
        "errors": state.errors_log,
        "validation_results": state.validation_results,
    }


@router.get("/runs")
async def list_runs() -> dict[str, Any]:
    """List all active pipeline runs."""
    return {
        "total_runs": len(_active_runs),
        "runs": [
            {
                "run_id": run_id,
                "summary": state.get_summary(),
            }
            for run_id, state in _active_runs.items()
        ],
    }
