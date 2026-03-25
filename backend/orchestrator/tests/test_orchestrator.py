"""Comprehensive tests for the multi-agent orchestration pipeline.

Tests cover:
1. PipelineState — serialization, versioning, error logging
2. BaseAgent — interface compliance, error wrapping
3. Orchestrator — dependency graph, topological sort, execution, retries
4. All 10 agents — individual run() methods, validation
5. End-to-end pipeline — full run with all agents
"""

from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, timezone

from backend.orchestrator.state import PipelineState
from backend.orchestrator.base_agent import (
    BaseAgent,
    AgentResult,
    FailureAction,
    ErrorType,
)
from backend.orchestrator.config import PipelineConfig
from backend.orchestrator.orchestrator import Orchestrator
from backend.orchestrator.agents import (
    IntentAnalyzerAgent,
    SchemaExplorerAgent,
    DataArchitectAgent,
    SQLWriterAgent,
    QueryOptimizerAgent,
    ProcedureWriterAgent,
    ExecutionAgent,
    GovernanceAgent,
    ValidationAgent,
    DocumentationAgent,
)


# ── Test Fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def state():
    return PipelineState(project_name="Test Pipeline")


@pytest.fixture
def config():
    return PipelineConfig(max_retries=2, parallel_limit=2)


# ── PipelineState Tests ───────────────────────────────────────────────

class TestPipelineState:
    def test_initialization(self, state):
        assert state.run_id is not None
        assert state.project_name == "Test Pipeline"
        assert state.version == 1
        assert state.task_status == {}
        assert state.outputs == {}
        assert state.errors_log == []

    def test_initialize_agent(self, state):
        state.initialize_agent("test_agent")
        assert state.task_status["test_agent"] == "pending"

    def test_update_state_task_status(self, state):
        state.initialize_agent("test_agent")
        state.update_state("test_agent", "task_status", "running")
        assert state.task_status["test_agent"] == "running"
        assert state.version == 2

    def test_update_state_outputs(self, state):
        state.update_state("test_agent", "outputs", {"key": "value"})
        assert state.outputs["test_agent"] == {"key": "value"}
        assert state.version == 2

    def test_update_state_increments_version(self, state):
        state.update_state("agent1", "outputs", {"a": 1})
        state.update_state("agent2", "outputs", {"b": 2})
        state.update_state("agent1", "task_status", "done")
        assert state.version == 4

    def test_log_error(self, state):
        state.log_error("test_agent", "RUNTIME_ERROR", "Test error")
        assert len(state.errors_log) == 1
        assert state.errors_log[0]["agent"] == "test_agent"
        assert state.errors_log[0]["error_type"] == "RUNTIME_ERROR"
        assert state.errors_log[0]["retry_count"] == 0

    def test_log_error_increments_retry_count(self, state):
        state.log_error("test_agent", "RUNTIME_ERROR", "Error 1")
        state.log_error("test_agent", "RUNTIME_ERROR", "Error 2")
        assert state.errors_log[0]["retry_count"] == 0
        assert state.errors_log[1]["retry_count"] == 1

    def test_get_retry_count(self, state):
        state.log_error("test_agent", "RUNTIME_ERROR", "Error 1")
        state.log_error("test_agent", "RUNTIME_ERROR", "Error 2")
        state.log_error("other_agent", "BUILD_ERROR", "Error 3")
        assert state.get_retry_count("test_agent") == 2
        assert state.get_retry_count("other_agent") == 1
        assert state.get_retry_count("unknown_agent") == 0

    def test_to_dict(self, state):
        state.update_state("agent1", "outputs", {"data": "value"})
        state.log_error("agent1", "RUNTIME_ERROR", "Test")
        d = state.to_dict()
        assert "run_id" in d
        assert "version" in d
        assert "task_status" in d
        assert "outputs" in d
        assert "errors_log" in d
        assert "validation_results" in d

    def test_from_dict(self, state):
        state.update_state("agent1", "outputs", {"data": "value"})
        state.update_state("agent1", "task_status", "done")
        d = state.to_dict()
        restored = PipelineState.from_dict(d)
        assert restored.run_id == state.run_id
        assert restored.version == state.version
        assert restored.outputs["agent1"] == {"data": "value"}
        assert restored.task_status["agent1"] == "done"

    def test_get_summary(self, state):
        state.initialize_agent("agent1")
        state.initialize_agent("agent2")
        state.initialize_agent("agent3")
        state.update_state("agent1", "task_status", "done")
        state.update_state("agent2", "task_status", "failed")
        state.update_state("agent3", "task_status", "pending")
        summary = state.get_summary()
        assert summary["total_agents"] == 3
        assert summary["completed"] == 1
        assert summary["failed"] == 1
        assert summary["pending"] == 1


# ── AgentResult Tests ─────────────────────────────────────────────────

class TestAgentResult:
    def test_success_result(self):
        result = AgentResult(success=True, output={"data": "value"})
        assert result.success is True
        assert bool(result) is True
        assert result.errors == []

    def test_failure_result(self):
        result = AgentResult(success=False, errors=["Error 1"])
        assert result.success is False
        assert bool(result) is False
        assert len(result.errors) == 1

    def test_default_values(self):
        result = AgentResult(success=True)
        assert result.output is None
        assert result.errors == []


# ── BaseAgent Tests ───────────────────────────────────────────────────

class TestBaseAgent:
    def test_validate_output_success(self):
        result = AgentResult(success=True, output={"key": "value"})
        agent = IntentAnalyzerAgent()
        assert agent.validate_output(result) is True

    def test_validate_output_failure(self):
        result = AgentResult(success=False, errors=["error"])
        agent = IntentAnalyzerAgent()
        assert agent.validate_output(result) is False

    def test_validate_output_none(self):
        result = AgentResult(success=True, output=None)
        agent = IntentAnalyzerAgent()
        assert agent.validate_output(result) is False

    def test_validate_output_empty_dict(self):
        result = AgentResult(success=True, output={})
        agent = IntentAnalyzerAgent()
        assert agent.validate_output(result) is False

    def test_validate_output_empty_list(self):
        result = AgentResult(success=True, output=[])
        agent = IntentAnalyzerAgent()
        assert agent.validate_output(result) is False

    def test_on_failure_retry(self, state):
        agent = IntentAnalyzerAgent()
        action = agent.on_failure(Exception("Test error"), state)
        assert action == FailureAction.RETRY

    def test_on_failure_abort_after_max_retries(self, state):
        agent = IntentAnalyzerAgent()
        # Simulate 3 previous errors
        for _ in range(3):
            state.log_error(agent.name, "RUNTIME_ERROR", "Error")
        action = agent.on_failure(Exception("Test error"), state)
        assert action == FailureAction.ABORT

    @pytest.mark.asyncio
    async def test_execute_wraps_exceptions(self, state):
        """Test that execute() catches exceptions and returns failed result."""

        class FailingAgent(BaseAgent):
            @property
            def name(self):
                return "failing_agent"

            @property
            def dependencies(self):
                return []

            async def run(self, state):
                raise ValueError("Intentional failure")

        agent = FailingAgent()
        result = await agent.execute(state)
        assert result.success is False
        assert len(result.errors) > 0
        assert state.task_status["failing_agent"] == "failed"
        assert len(state.errors_log) == 1

    @pytest.mark.asyncio
    async def test_execute_success(self, state):
        """Test that execute() returns success and updates state."""

        class SuccessAgent(BaseAgent):
            @property
            def name(self):
                return "success_agent"

            @property
            def dependencies(self):
                return []

            async def run(self, state):
                return AgentResult(success=True, output={"data": "value"})

        agent = SuccessAgent()
        result = await agent.execute(state)
        assert result.success is True
        assert state.task_status["success_agent"] == "done"


# ── Orchestrator Tests ────────────────────────────────────────────────

class TestOrchestrator:
    def test_build_dependency_graph(self, state, config):
        agents = [
            IntentAnalyzerAgent(),
            SchemaExplorerAgent(),
            DataArchitectAgent(),
        ]
        orchestrator = Orchestrator(agents, state, config)
        graph = orchestrator.build_dependency_graph()
        assert "intent_analyzer" in graph
        assert "schema_explorer" in graph
        assert "data_architect" in graph
        assert graph["intent_analyzer"] == []
        assert graph["schema_explorer"] == ["intent_analyzer"]

    def test_topological_sort(self, state, config):
        agents = [
            IntentAnalyzerAgent(),
            SchemaExplorerAgent(),
            DataArchitectAgent(),
        ]
        orchestrator = Orchestrator(agents, state, config)
        order = orchestrator.topological_sort()
        # intent_analyzer must come before schema_explorer and data_architect
        assert order.index("intent_analyzer") < order.index("schema_explorer")
        assert order.index("intent_analyzer") < order.index("data_architect")
        # schema_explorer must come before data_architect
        assert order.index("schema_explorer") < order.index("data_architect")

    def test_topological_sort_detects_cycle(self, state, config):
        """Test that circular dependencies are detected."""

        class CycleAgentA(BaseAgent):
            @property
            def name(self):
                return "cycle_a"

            @property
            def dependencies(self):
                return ["cycle_b"]

            async def run(self, state):
                return AgentResult(success=True, output={})

        class CycleAgentB(BaseAgent):
            @property
            def name(self):
                return "cycle_b"

            @property
            def dependencies(self):
                return ["cycle_a"]

            async def run(self, state):
                return AgentResult(success=True, output={})

        agents = [CycleAgentA(), CycleAgentB()]
        orchestrator = Orchestrator(agents, state, config)
        orchestrator.build_dependency_graph()

        with pytest.raises(ValueError, match="Circular dependency"):
            orchestrator.topological_sort()

    @pytest.mark.asyncio
    async def test_run_pipeline(self, state, config):
        """Test running a simple pipeline with 3 agents."""
        state.user_intent = {"prompt": "Design a schema and write queries"}
        state.selected_skills = ["data-architect"]
        agents = [
            IntentAnalyzerAgent(),
            SchemaExplorerAgent(),
            DataArchitectAgent(),
        ]
        orchestrator = Orchestrator(agents, state, config)
        orchestrator.register_checkpoint("intent_analyzer", "intent_validation")
        orchestrator.register_checkpoint("schema_explorer", "schema_consistency")

        result = await orchestrator.run()

        assert result["status"] in ("completed", "completed_with_skips")
        assert state.task_status.get("intent_analyzer") == "done"
        assert state.task_status.get("schema_explorer") == "done"
        assert state.task_status.get("data_architect") == "done"
        assert "intent_validation" in state.validation_results
        assert "schema_consistency" in state.validation_results

    def test_register_checkpoint(self, state, config):
        agents = [IntentAnalyzerAgent()]
        orchestrator = Orchestrator(agents, state, config)
        orchestrator.register_checkpoint("intent_analyzer", "test_checkpoint")
        assert "intent_analyzer" in orchestrator._checkpoints
        assert orchestrator._checkpoints["intent_analyzer"] == "test_checkpoint"


# ── Individual Agent Tests ────────────────────────────────────────────

class TestIntentAnalyzerAgent:
    @pytest.mark.asyncio
    async def test_run_with_intent(self, state):
        state.user_intent = {"prompt": "Create a star schema for order analytics"}
        state.selected_skills = ["data-architect"]
        agent = IntentAnalyzerAgent()
        result = await agent.run(state)
        assert result.success is True
        assert "all_skills" in result.output
        assert "complexity" in result.output
        assert "execution_path" in result.output

    @pytest.mark.asyncio
    async def test_run_with_no_intent(self, state):
        agent = IntentAnalyzerAgent()
        result = await agent.run(state)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_detects_skills_from_prompt(self, state):
        state.user_intent = {"prompt": "Write a SQL query to join orders with customers"}
        state.selected_skills = []
        agent = IntentAnalyzerAgent()
        result = await agent.run(state)
        assert result.success is True
        assert "sql-writer" in result.output["detected_skills"]

    def test_validate_output(self):
        agent = IntentAnalyzerAgent()
        result = AgentResult(success=True, output={"all_skills": ["sql-writer"], "complexity": "simple"})
        assert agent.validate_output(result) is True


class TestSchemaExplorerAgent:
    @pytest.mark.asyncio
    async def test_run(self, state):
        state.user_intent = {"prompt": "Design a schema for orders"}
        state.selected_skills = ["data-architect"]
        # Pre-populate intent analyzer output
        state.outputs["intent_analyzer"] = {
            "all_skills": ["data-architect"],
            "execution_path": "design_and_build",
            "complexity": "moderate",
        }
        agent = SchemaExplorerAgent()
        result = await agent.run(state)
        assert result.success is True
        assert len(result.output["databases"]) > 0

    @pytest.mark.asyncio
    async def test_run_no_intent(self, state):
        agent = SchemaExplorerAgent()
        result = await agent.run(state)
        assert result.success is False


class TestDataArchitectAgent:
    @pytest.mark.asyncio
    async def test_run_dimensional(self, state):
        state.user_intent = {"prompt": "Design a star schema for order analytics with customer and product dimensions"}
        state.outputs["intent_analyzer"] = {
            "all_skills": ["data-architect"],
            "execution_path": "design_and_build",
            "complexity": "complex",
        }
        state.outputs["schema_explorer"] = {
            "databases": [{"name": "CURATED_DB", "purpose": "Analytics"}],
            "exploration_strategy": "full_exploration",
        }
        agent = DataArchitectAgent()
        result = await agent.run(state)
        assert result.success is True
        assert result.output["paradigm"] == "dimensional"
        assert len(result.output["entities"]) > 0

    def test_validate_output(self):
        agent = DataArchitectAgent()
        result = AgentResult(success=True, output={"paradigm": "dimensional", "entities": [{"name": "fct_orders"}]})
        assert agent.validate_output(result) is True


class TestSQLWriterAgent:
    @pytest.mark.asyncio
    async def test_run(self, state):
        state.user_intent = {"prompt": "Select all orders"}
        state.outputs["data_architect"] = {
            "paradigm": "dimensional",
            "entities": [{"name": "fct_orders", "type": "fact"}],
            "relationships": [],
        }
        agent = SQLWriterAgent()
        result = await agent.run(state)
        assert result.success is True
        assert len(result.output["queries"]) > 0

    def test_validate_output(self):
        agent = SQLWriterAgent()
        result = AgentResult(success=True, output={"queries": ["SELECT * FROM fct_orders;"]})
        assert agent.validate_output(result) is True


class TestQueryOptimizerAgent:
    @pytest.mark.asyncio
    async def test_run(self, state):
        state.user_intent = {"prompt": "Select all orders"}
        state.outputs["sql_writer"] = {
            "queries": ["SELECT * FROM fct_orders"],
            "dialect": "snowflake",
        }
        agent = QueryOptimizerAgent()
        result = await agent.run(state)
        assert result.success is True
        assert len(result.output["optimized_queries"]) > 0

    def test_optimize_adds_limit(self):
        agent = QueryOptimizerAgent()
        optimized, recs = agent._optimize_query("SELECT * FROM fct_orders")
        assert "LIMIT" in optimized.upper()

    def test_optimize_detects_select_star(self):
        agent = QueryOptimizerAgent()
        _, recs = agent._optimize_query("SELECT * FROM fct_orders LIMIT 100;")
        assert any("SELECT *" in r for r in recs)


class TestExecutionAgent:
    @pytest.mark.asyncio
    async def test_run(self, state):
        state.outputs["query_optimizer"] = {
            "optimized_queries": ["SELECT 1;"],
            "recommendations": [],
        }
        state.outputs["sql_writer"] = {
            "queries": ["SELECT 1;"],
        }
        agent = ExecutionAgent()
        result = await agent.run(state)
        assert result.success is True
        assert result.output["queries_executed"] == 1

    @pytest.mark.asyncio
    async def test_run_no_queries(self, state):
        state.outputs["query_optimizer"] = {"optimized_queries": []}
        state.outputs["sql_writer"] = {"queries": []}
        agent = ExecutionAgent()
        result = await agent.run(state)
        assert result.success is False

    def test_validate_query_syntax(self):
        agent = ExecutionAgent()
        assert agent._validate_query_syntax("SELECT * FROM t")["valid"] is True
        assert agent._validate_query_syntax("")["valid"] is False
        assert agent._validate_query_syntax("INVALID query")["valid"] is False
        assert agent._validate_query_syntax("SELECT (a FROM t")["valid"] is False


class TestGovernanceAgent:
    @pytest.mark.asyncio
    async def test_run(self, state):
        state.outputs["execution_agent"] = {
            "queries_executed": 1,
            "all_succeeded": True,
            "estimated_tokens_used": 100,
            "total_execution_time_ms": 50,
            "failed_queries": [],
        }
        state.token_usage = {"execution_agent": 100}
        state.cost_tracking = {}
        agent = GovernanceAgent()
        result = await agent.run(state)
        assert result.success is True
        assert "compliance" in result.output
        assert "cost_analysis" in result.output


class TestValidationAgent:
    @pytest.mark.asyncio
    async def test_run(self, state):
        # Set up all required outputs
        state.outputs["intent_analyzer"] = {
            "all_skills": ["sql-writer"],
            "complexity": "simple",
            "execution_path": "query_workflow",
        }
        state.outputs["schema_explorer"] = {
            "databases": [{"name": "CURATED_DB"}],
            "exploration_strategy": "targeted",
        }
        state.outputs["data_architect"] = {
            "paradigm": "dimensional",
            "entities": [{"name": "fct_orders"}],
        }
        state.outputs["sql_writer"] = {
            "queries": ["SELECT 1;"],
            "dialect": "snowflake",
        }
        state.outputs["execution_agent"] = {
            "queries_executed": 1,
            "all_succeeded": True,
            "failed_queries": [],
            "total_execution_time_ms": 10,
        }
        state.outputs["governance_agent"] = {
            "compliance": {"compliant": True, "risk_level": "low", "issues": []},
            "cost_analysis": {"estimated_cost": 0.001},
            "security_checks": {"sql_injection_risk": "low"},
        }
        agent = ValidationAgent()
        result = await agent.run(state)
        assert result.success is True
        assert result.output["all_passed"] is True
        assert result.output["overall_status"] == "passed"


class TestDocumentationAgent:
    @pytest.mark.asyncio
    async def test_run(self, state):
        # Set up minimal outputs from all agents
        state.outputs["intent_analyzer"] = {"all_skills": [], "complexity": "simple", "execution_path": "simple_query"}
        state.outputs["schema_explorer"] = {"databases": [], "exploration_strategy": "minimal"}
        state.outputs["data_architect"] = {"paradigm": "dimensional", "entities": [], "relationships": []}
        state.outputs["sql_writer"] = {"queries": [], "dialect": "snowflake"}
        state.outputs["query_optimizer"] = {"optimized_queries": [], "recommendations": []}
        state.outputs["execution_agent"] = {"queries_executed": 0, "all_succeeded": True, "total_execution_time_ms": 0, "failed_queries": []}
        state.outputs["governance_agent"] = {"compliance": {}, "cost_analysis": {}, "security_checks": {}, "recommendations": []}
        state.outputs["validation_agent"] = {"overall_status": "passed", "validations": {}}

        agent = DocumentationAgent()
        result = await agent.run(state)
        assert result.success is True
        assert "documentation" in result.output
        doc = result.output["documentation"]
        assert "metadata" in doc


# ── End-to-End Pipeline Test ──────────────────────────────────────────

class TestEndToEndPipeline:
    @pytest.mark.asyncio
    async def test_full_pipeline_run(self):
        """Test the complete pipeline with all 10 agents."""
        state = PipelineState(
            project_name="E2E Test Pipeline",
            user_intent={"prompt": "Design a star schema for order analytics and write queries"},
            selected_skills=["data-architect", "sql-writer", "query-optimizer"],
        )

        config = PipelineConfig(max_retries=2, parallel_limit=3)

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

        orchestrator = Orchestrator(agents, state, config)

        # Register all checkpoints
        orchestrator.register_checkpoint("intent_analyzer", "intent_validation")
        orchestrator.register_checkpoint("schema_explorer", "schema_consistency")
        orchestrator.register_checkpoint("sql_writer", "sql_syntax_check")
        orchestrator.register_checkpoint("execution_agent", "execution_validation")
        orchestrator.register_checkpoint("governance_agent", "governance_compliance")

        result = await orchestrator.run()

        # Verify all agents ran
        assert state.task_status.get("intent_analyzer") == "done"
        assert state.task_status.get("schema_explorer") == "done"
        assert state.task_status.get("data_architect") == "done"
        assert state.task_status.get("sql_writer") == "done"
        assert state.task_status.get("query_optimizer") == "done"
        assert state.task_status.get("procedure_writer") == "done"
        assert state.task_status.get("execution_agent") == "done"
        assert state.task_status.get("governance_agent") == "done"
        assert state.task_status.get("validation_agent") == "done"
        assert state.task_status.get("documentation_agent") == "done"

        # Verify pipeline completed
        assert result["status"] in ("completed", "completed_with_skips")

        # Verify validation ran
        assert "validations" in state.outputs.get("validation_agent", {})

        # Verify documentation was generated
        assert "documentation" in state.outputs.get("documentation_agent", {})

        # Verify state versioning
        assert state.version > 1

        # Verify no silent failures
        failed_agents = [
            name for name, status in state.task_status.items()
            if status == "failed"
        ]
        assert len(failed_agents) == 0, f"Failed agents: {failed_agents}"

    @pytest.mark.asyncio
    async def test_pipeline_with_empty_input(self):
        """Test pipeline behavior with minimal input."""
        state = PipelineState(
            project_name="Minimal Test",
            user_intent={"prompt": ""},
            selected_skills=[],
        )

        config = PipelineConfig(max_retries=1, parallel_limit=1)

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

        orchestrator = Orchestrator(agents, state, config)
        result = await orchestrator.run()

        # Pipeline should complete even with empty input (agents handle gracefully)
        assert "status" in result
        assert state.task_status.get("documentation_agent") in ("done", "skipped")
