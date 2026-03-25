"""Orchestrator — the central execution engine for the multi-agent pipeline.

The orchestrator is the ONLY component allowed to call agents. It:
1. Builds a dependency graph from each agent's `dependencies` field
2. Resolves execution order via topological sort
3. Runs agents whose dependencies are all `done` — in parallel where possible
4. Validates output after each agent, updates shared state
5. Runs validation gates at defined checkpoints
6. Handles failures with retry/skip/abort recovery
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any

from .base_agent import AgentResult, BaseAgent, ErrorType, FailureAction
from .config import PipelineConfig
from .state import PipelineState

logger = logging.getLogger(__name__)


class Orchestrator:
    """Manages the full lifecycle of a multi-agent execution pipeline.

    Args:
        agents: List of BaseAgent instances to orchestrate.
        state: Shared PipelineState (source of truth for the entire run).
        config: PipelineConfig controlling retries, parallelism, etc.
    """

    def __init__(
        self,
        agents: list[BaseAgent],
        state: PipelineState,
        config: PipelineConfig | None = None,
    ) -> None:
        self.agents = {agent.name: agent for agent in agents}
        self.state = state
        self.config = config or PipelineConfig()
        self._dependency_graph: dict[str, list[str]] = {}
        self._reverse_graph: dict[str, list[str]] = defaultdict(list)
        self._checkpoints: dict[str, str] = {}  # agent_name → checkpoint_name
        self._lock = asyncio.Lock()

    # ── Dependency Graph ──────────────────────────────────────────────

    def build_dependency_graph(self) -> dict[str, list[str]]:
        """Build adjacency list from each agent's dependencies.

        Returns:
            Dict mapping agent_name → list of agents that depend on it.
        """
        self._dependency_graph = {}
        self._reverse_graph = defaultdict(list)

        for name, agent in self.agents.items():
            deps = agent.dependencies
            self._dependency_graph[name] = deps
            for dep in deps:
                self._reverse_graph[dep].append(name)
            self.state.initialize_agent(name)

        logger.info(
            "Built dependency graph for %d agents: %s",
            len(self.agents),
            {k: v for k, v in self._dependency_graph.items()},
        )
        return self._dependency_graph

    def topological_sort(self) -> list[str]:
        """Resolve execution order via Kahn's algorithm (topological sort).

        Returns:
            List of agent names in valid execution order.

        Raises:
            ValueError: If a circular dependency is detected.
        """
        in_degree: dict[str, int] = {name: 0 for name in self.agents}

        for name, deps in self._dependency_graph.items():
            in_degree[name] = len(deps)

        queue: list[str] = [name for name, degree in in_degree.items() if degree == 0]
        result: list[str] = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for dependent in self._reverse_graph.get(node, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(self.agents):
            missing = set(self.agents.keys()) - set(result)
            raise ValueError(
                f"Circular dependency detected among agents: {missing}"
            )

        logger.info("Topological sort order: %s", result)
        return result

    # ── Checkpoint Registration ───────────────────────────────────────

    def register_checkpoint(self, after_agent: str, checkpoint_name: str) -> None:
        """Register a validation gate to run after a specific agent completes.

        Args:
            after_agent: The agent after which the checkpoint runs.
            checkpoint_name: Name of the checkpoint (used in validation_results).
        """
        self._checkpoints[after_agent] = checkpoint_name
        logger.info("Registered checkpoint '%s' after agent '%s'", checkpoint_name, after_agent)

    # ── Main Pipeline Execution ───────────────────────────────────────

    async def run(self) -> dict[str, Any]:
        """Execute the full pipeline from start to finish.

        Returns:
            A dict with pipeline summary: status, completed agents, errors, etc.
        """
        self.build_dependency_graph()
        execution_order = self.topological_sort()

        logger.info(
            "Starting pipeline '%s' (run_id=%s, agents=%d)",
            self.state.project_name,
            self.state.run_id,
            len(self.agents),
        )

        semaphore = asyncio.Semaphore(self.config.parallel_limit)

        async def run_with_semaphore(agent: BaseAgent) -> AgentResult:
            async with semaphore:
                return await self._execute_agent(agent)

        for agent_name in execution_order:
            agent = self.agents[agent_name]

            # Check if all dependencies are satisfied
            deps_satisfied = all(
                self.state.task_status.get(dep) == "done"
                for dep in agent.dependencies
            )

            if not deps_satisfied:
                failed_deps = [
                    dep
                    for dep in agent.dependencies
                    if self.state.task_status.get(dep) in ("failed", "skipped")
                ]
                if failed_deps:
                    logger.warning(
                        "Skipping agent '%s': dependencies failed: %s",
                        agent_name,
                        failed_deps,
                    )
                    self.state.update_state(agent_name, "task_status", "skipped")
                    self.state.log_error(
                        agent_name,
                        ErrorType.DEPENDENCY_ERROR.value,
                        f"Dependencies failed: {failed_deps}",
                    )
                    continue

                # Dependencies still running — shouldn't happen with topo sort,
                # but handle defensively
                logger.warning(
                    "Agent '%s' has incomplete dependencies, waiting...",
                    agent_name,
                )
                await asyncio.sleep(0.1)

            result = await run_with_semaphore(agent)

            # Validate output
            if result.success and not agent.validate_output(result):
                logger.warning(
                    "Agent '%s' output failed validation",
                    agent_name,
                )
                self.state.log_error(
                    agent_name,
                    ErrorType.VALIDATION_ERROR.value,
                    "Output validation failed",
                )
                result = AgentResult(
                    success=False,
                    output=result.output,
                    errors=result.errors + ["Output validation failed"],
                )
                self.state.update_state(agent_name, "task_status", "failed")

            # Run checkpoint if registered
            if agent_name in self._checkpoints:
                checkpoint_name = self._checkpoints[agent_name]
                await self._run_checkpoint(agent_name, checkpoint_name)

        return self._build_summary()

    # ── Agent Execution with Retry ────────────────────────────────────

    async def _execute_agent(self, agent: BaseAgent) -> AgentResult:
        """Execute a single agent with retry logic.

        Args:
            agent: The agent to execute.

        Returns:
            AgentResult from the agent's run() method.
        """
        max_retries = self.config.max_retries
        backoff = self.config.retry_backoff_base

        for attempt in range(max_retries + 1):
            if attempt > 0:
                wait_time = backoff ** attempt
                logger.info(
                    "Retrying agent '%s' (attempt %d/%d) in %.1fs",
                    agent.name,
                    attempt,
                    max_retries,
                    wait_time,
                )
                await asyncio.sleep(wait_time)

            result = await agent.execute(self.state)

            if result.success:
                # Write output to shared state
                self.state.update_state(agent.name, "outputs", result.output)
                return result

            # Handle failure
            action = agent.on_failure(Exception("; ".join(result.errors)), self.state)

            if action == FailureAction.ABORT:
                logger.error("Agent '%s' aborted after failure", agent.name)
                return result

            if action == FailureAction.SKIP:
                logger.warning("Agent '%s' skipped after failure", agent.name)
                self.state.update_state(agent.name, "task_status", "skipped")
                return result

            # RETRY — continue loop
            logger.info(
                "Agent '%s' will retry (attempt %d/%d)",
                agent.name,
                attempt + 1,
                max_retries,
            )

        # Exhausted all retries
        logger.error(
            "Agent '%s' failed after %d retries",
            agent.name,
            max_retries,
        )
        return AgentResult(
            success=False,
            output=None,
            errors=[f"Failed after {max_retries} retries"],
        )

    # ── Validation Gates ──────────────────────────────────────────────

    async def _run_checkpoint(self, agent_name: str, checkpoint_name: str) -> None:
        """Run a validation gate after an agent completes.

        Args:
            agent_name: The agent that just completed.
            checkpoint_name: Name of the checkpoint to run.
        """
        logger.info("Running checkpoint '%s' after agent '%s'", checkpoint_name, agent_name)

        # Default checkpoint: verify the agent produced valid output
        output = self.state.outputs.get(agent_name)
        passed = output is not None

        details = {
            "agent": agent_name,
            "checkpoint": checkpoint_name,
            "passed": passed,
            "timestamp": self.state.last_updated.isoformat(),
        }

        if not passed:
            details["reason"] = f"No output from agent '{agent_name}'"
            logger.warning("Checkpoint '%s' FAILED: %s", checkpoint_name, details["reason"])

            if self.config.checkpoint_strict_mode:
                self.state.log_error(
                    agent_name,
                    ErrorType.VALIDATION_ERROR.value,
                    f"Checkpoint '{checkpoint_name}' failed in strict mode",
                )
        else:
            logger.info("Checkpoint '%s' PASSED", checkpoint_name)

        self.state.validation_results[checkpoint_name] = details
        # Also update agent's validation_results in state
        self.state.update_state(agent_name, "validation_results", details)

    # ── Summary ───────────────────────────────────────────────────────

    def _build_summary(self) -> dict[str, Any]:
        """Build a comprehensive summary of the pipeline run."""
        return {
            "status": self._determine_status(),
            "summary": self.state.get_summary(),
            "state": self.state.to_dict(),
            "checkpoints": self.state.validation_results,
            "errors": self.state.errors_log,
        }

    def _determine_status(self) -> str:
        """Determine overall pipeline status."""
        statuses = list(self.state.task_status.values())

        if not statuses:
            return "empty"

        failed = sum(1 for s in statuses if s == "failed")
        skipped = sum(1 for s in statuses if s == "skipped")
        done = sum(1 for s in statuses if s == "done")
        total = len(statuses)

        if failed > 0 and self.config.checkpoint_strict_mode:
            return "failed"

        if done == total:
            return "completed"

        if done + skipped == total:
            return "completed_with_skips"

        if failed + skipped > total // 2:
            return "degraded"

        return "partial"
