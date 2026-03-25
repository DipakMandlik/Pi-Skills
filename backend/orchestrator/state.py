"""Shared state layer for the multi-agent orchestration pipeline.

This is the single source of truth that all agents read from and write to.
No agent-to-agent direct calls — all communication flows through this state.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class PipelineState:
    """Versioned shared state for the entire orchestration pipeline.

    Every agent reads from and writes to this object. All writes are
    versioned and timestamped for debugging and audit purposes.
    """

    # --- Project metadata ---
    run_id: str = field(default_factory=lambda: str(uuid4()))
    project_name: str = "AI Governance Pipeline"
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # --- Agent tracking: agent_name → "pending"|"running"|"done"|"failed"|"skipped" ---
    task_status: dict[str, str] = field(default_factory=dict)

    # --- Agent outputs: agent_name → their structured output artifact ---
    outputs: dict[str, Any] = field(default_factory=dict)

    # --- User context ---
    user_intent: dict[str, Any] = field(default_factory=dict)
    selected_skills: list[str] = field(default_factory=list)
    user_id: str | None = None

    # --- Snowflake context ---
    snowflake_metadata: dict[str, Any] = field(default_factory=dict)

    # --- Governance ---
    token_usage: dict[str, int] = field(default_factory=dict)
    cost_tracking: dict[str, float] = field(default_factory=dict)

    # --- Error log ---
    errors_log: list[dict[str, Any]] = field(default_factory=list)

    # --- Validation results: checkpoint_name → {"passed": bool, "details": str} ---
    validation_results: dict[str, dict[str, Any]] = field(default_factory=dict)

    # --- Versioning ---
    version: int = 1
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def initialize_agent(self, agent_name: str) -> None:
        """Mark an agent as pending in the task status map."""
        if agent_name not in self.task_status:
            self.task_status[agent_name] = "pending"

    def update_state(
        self,
        agent_name: str,
        field_name: str,
        value: Any,
    ) -> None:
        """Update a field in the state with versioning and timestamping.

        Args:
            agent_name: The agent performing the update.
            field_name: The name of the field to update.
            value: The new value.
        """
        self.version += 1
        self.last_updated = datetime.now(timezone.utc)

        if field_name == "task_status":
            self.task_status[agent_name] = value
        elif field_name == "outputs":
            self.outputs[agent_name] = value
        elif field_name == "user_intent":
            self.user_intent = value
        elif field_name == "snowflake_metadata":
            self.snowflake_metadata = value
        elif field_name == "token_usage":
            self.token_usage.update(value)
        elif field_name == "cost_tracking":
            self.cost_tracking.update(value)
        elif field_name == "validation_results":
            self.validation_results[agent_name] = value
        else:
            setattr(self, field_name, value)

        logger.debug(
            "State updated: agent=%s field=%s version=%s",
            agent_name,
            field_name,
            self.version,
        )

    def log_error(
        self,
        agent_name: str,
        error_type: str,
        message: str,
        stack_trace: str | None = None,
    ) -> None:
        """Log an error to the errors_log with retry tracking.

        Args:
            agent_name: The agent that encountered the error.
            error_type: Classification of the error (e.g. RUNTIME_ERROR).
            message: Human-readable error message.
            stack_trace: Optional full stack trace for debugging.
        """
        retry_count = sum(
            1
            for entry in self.errors_log
            if entry["agent"] == agent_name
        )

        error_entry = {
            "agent": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_type": error_type,
            "message": message,
            "stack_trace": stack_trace,
            "retry_count": retry_count,
        }
        self.errors_log.append(error_entry)
        logger.error(
            "Error logged: agent=%s type=%s message=%s retry_count=%s",
            agent_name,
            error_type,
            message,
            retry_count,
        )

    def get_retry_count(self, agent_name: str) -> int:
        """Get the current retry count for an agent."""
        return sum(
            1
            for entry in self.errors_log
            if entry["agent"] == agent_name
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize state to a dictionary (for persistence or API response)."""
        return {
            "run_id": self.run_id,
            "project_name": self.project_name,
            "started_at": self.started_at.isoformat(),
            "task_status": dict(self.task_status),
            "outputs": {k: str(v) if not isinstance(v, (dict, list)) else v for k, v in self.outputs.items()},
            "user_intent": self.user_intent,
            "selected_skills": list(self.selected_skills),
            "user_id": self.user_id,
            "snowflake_metadata": self.snowflake_metadata,
            "token_usage": dict(self.token_usage),
            "cost_tracking": dict(self.cost_tracking),
            "errors_log": list(self.errors_log),
            "validation_results": self.validation_results,
            "version": self.version,
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipelineState":
        """Deserialize state from a dictionary."""
        state = cls(
            run_id=data.get("run_id", str(uuid4())),
            project_name=data.get("project_name", "AI Governance Pipeline"),
            started_at=datetime.fromisoformat(data["started_at"])
            if "started_at" in data
            else datetime.now(timezone.utc),
            task_status=data.get("task_status", {}),
            outputs=data.get("outputs", {}),
            user_intent=data.get("user_intent", {}),
            selected_skills=data.get("selected_skills", []),
            user_id=data.get("user_id"),
            snowflake_metadata=data.get("snowflake_metadata", {}),
            token_usage=data.get("token_usage", {}),
            cost_tracking=data.get("cost_tracking", {}),
            errors_log=data.get("errors_log", []),
            validation_results=data.get("validation_results", {}),
            version=data.get("version", 1),
            last_updated=datetime.fromisoformat(data["last_updated"])
            if "last_updated" in data
            else datetime.now(timezone.utc),
        )
        return state

    def get_summary(self) -> dict[str, Any]:
        """Get a concise summary of the pipeline state."""
        total = len(self.task_status)
        done = sum(1 for s in self.task_status.values() if s == "done")
        failed = sum(1 for s in self.task_status.values() if s == "failed")
        skipped = sum(1 for s in self.task_status.values() if s == "skipped")
        running = sum(1 for s in self.task_status.values() if s == "running")
        pending = sum(1 for s in self.task_status.values() if s == "pending")

        return {
            "run_id": self.run_id,
            "project_name": self.project_name,
            "version": self.version,
            "total_agents": total,
            "completed": done,
            "failed": failed,
            "skipped": skipped,
            "running": running,
            "pending": pending,
            "total_errors": len(self.errors_log),
            "checkpoints_passed": sum(
                1 for v in self.validation_results.values() if v.get("passed")
            ),
            "checkpoints_failed": sum(
                1 for v in self.validation_results.values() if not v.get("passed")
            ),
        }
