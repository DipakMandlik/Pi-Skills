"""Base agent interface for the multi-agent orchestration pipeline.

Every agent in the system must implement this contract. The orchestrator
uses these interfaces to manage execution, validation, and error recovery.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .state import PipelineState

logger = logging.getLogger(__name__)


class FailureAction(Enum):
    """Actions the orchestrator can take when an agent fails."""
    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"


class ErrorType(Enum):
    """Classification of errors caught during agent execution."""
    BUILD_ERROR = "BUILD_ERROR"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONTRACT_ERROR = "CONTRACT_ERROR"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"


@dataclass
class AgentResult:
    """Structured result from an agent execution.

    Every agent returns this — never raw strings or untyped dicts.
    """
    success: bool
    output: Any = None
    errors: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.success


class BaseAgent(ABC):
    """Abstract base class that all agents must implement.

    Subclass this and implement `name`, `dependencies`, and `run`.
    Override `validate_output` and `on_failure` for custom behavior.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this agent."""
        ...

    @property
    @abstractmethod
    def dependencies(self) -> list[str]:
        """List of agent names that must complete before this agent runs."""
        ...

    @abstractmethod
    async def run(self, state: PipelineState) -> AgentResult:
        """Execute the agent's primary logic.

        Args:
            state: The shared pipeline state. Read inputs from
                   state.outputs[dependency_name] and write results
                   via the returned AgentResult.

        Returns:
            AgentResult with success flag, output data, and any errors.
        """
        ...

    def validate_output(self, result: AgentResult) -> bool:
        """Validate the agent's output before passing to downstream agents.

        Override this to add agent-specific validation logic.
        Default: checks that the result is successful and output is not None.

        Args:
            result: The AgentResult returned by run().

        Returns:
            True if the output is valid, False otherwise.
        """
        if not result.success:
            return False
        if result.output is None:
            return False
        if isinstance(result.output, dict) and len(result.output) == 0:
            return False
        if isinstance(result.output, list) and len(result.output) == 0:
            return False
        return True

    def on_failure(
        self,
        error: Exception,
        state: PipelineState,
    ) -> FailureAction:
        """Determine the recovery action when this agent fails.

        Override for custom retry logic. Default: retry up to 3 times,
        then abort.

        Args:
            error: The exception that was raised.
            state: The current pipeline state (for retry count lookup).

        Returns:
            The FailureAction the orchestrator should take.
        """
        retry_count = state.get_retry_count(self.name)
        if retry_count < 3:
            logger.info(
                "Agent %s failed (retry %d/3), will retry: %s",
                self.name,
                retry_count + 1,
                error,
            )
            return FailureAction.RETRY
        logger.error(
            "Agent %s failed after %d retries, aborting: %s",
            self.name,
            retry_count,
            error,
        )
        return FailureAction.ABORT

    async def execute(self, state: PipelineState) -> AgentResult:
        """Execute the agent with logging and error wrapping.

        This is the method the orchestrator calls. It wraps run() in
        a try/except so no agent can crash the orchestrator.

        Args:
            state: The shared pipeline state.

        Returns:
            AgentResult from run(), or a failed result if an exception occurred.
        """
        logger.info("Agent %s starting (version=%s)", self.name, state.version)
        state.update_state(self.name, "task_status", "running")

        try:
            result = await self.run(state)
        except Exception as e:
            logger.exception("Agent %s raised an exception: %s", self.name, e)
            state.log_error(
                self.name,
                ErrorType.RUNTIME_ERROR.value,
                str(e),
                stack_trace=str(e),
            )
            result = AgentResult(
                success=False,
                output=None,
                errors=[str(e)],
            )

        if result.success:
            state.update_state(self.name, "task_status", "done")
            logger.info("Agent %s completed successfully", self.name)
        else:
            state.update_state(self.name, "task_status", "failed")
            logger.warning(
                "Agent %s returned a failed result: %s",
                self.name,
                result.errors,
            )

        return result
