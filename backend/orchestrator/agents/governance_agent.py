"""Governance Agent — tracks token usage, costs, and security compliance."""

from __future__ import annotations

import logging
from typing import Any

from ..base_agent import AgentResult, BaseAgent
from ..state import PipelineState

logger = logging.getLogger(__name__)


class GovernanceAgent(BaseAgent):
    """Monitors token usage, costs, and security compliance.

    Runs after execution to track resource consumption, validate
    against budget limits, and perform security checks.
    """

    @property
    def name(self) -> str:
        return "governance_agent"

    @property
    def dependencies(self) -> list[str]:
        return ["execution_agent"]

    async def run(self, state: PipelineState) -> AgentResult:
        """Analyze governance metrics after execution.

        Reads execution results, token usage, and cost tracking from state.
        Validates against budget limits and security policies.
        """
        execution_output = state.outputs.get("execution_agent")
        if not execution_output:
            return AgentResult(
                success=False,
                errors=["No execution results available from execution_agent"],
            )

        # Gather governance metrics
        token_usage = state.token_usage
        cost_tracking = state.cost_tracking
        errors_log = state.errors_log

        # Analyze execution results
        queries_executed = execution_output.get("queries_executed", 0)
        estimated_tokens = execution_output.get("estimated_tokens_used", 0)
        execution_time_ms = execution_output.get("total_execution_time_ms", 0)
        failed_queries = execution_output.get("failed_queries", [])

        # Cost analysis
        cost_analysis = self._analyze_costs(token_usage, cost_tracking)

        # Security checks
        security_checks = self._run_security_checks(state)

        # Compliance assessment
        compliance = self._assess_compliance(
            token_usage=token_usage,
            cost_analysis=cost_analysis,
            security_checks=security_checks,
            errors_log=errors_log,
        )

        result = {
            "queries_executed": queries_executed,
            "failed_queries": len(failed_queries),
            "token_usage": token_usage,
            "estimated_tokens": estimated_tokens,
            "execution_time_ms": execution_time_ms,
            "cost_analysis": cost_analysis,
            "security_checks": security_checks,
            "compliance": compliance,
            "recommendations": self._generate_recommendations(compliance, cost_analysis),
        }

        state.update_state(self.name, "outputs", result)
        state.update_state(self.name, "token_usage", token_usage)
        state.update_state(self.name, "cost_tracking", cost_tracking)

        return AgentResult(success=True, output=result)

    def _analyze_costs(
        self,
        token_usage: dict[str, int],
        cost_tracking: dict[str, float],
    ) -> dict[str, Any]:
        """Analyze cost metrics."""
        total_tokens = sum(token_usage.values())
        total_cost = sum(cost_tracking.values())

        # Estimate cost based on tokens (using average rate of $0.003/1K tokens)
        estimated_cost = (total_tokens / 1000) * 0.003

        return {
            "total_tokens": total_tokens,
            "total_tracked_cost": round(total_cost, 6),
            "estimated_cost": round(estimated_cost, 6),
            "token_breakdown": token_usage,
            "cost_breakdown": cost_tracking,
        }

    def _run_security_checks(self, state: PipelineState) -> dict[str, Any]:
        """Run security compliance checks."""
        checks = {
            "sql_injection_risk": "low",
            "pii_exposure": "none_detected",
            "permission_violations": [],
            "audit_trail_complete": True,
        }

        # Check for potentially dangerous SQL patterns
        sql_output = state.outputs.get("sql_writer", {})
        queries = sql_output.get("queries", [])

        dangerous_patterns = ["DROP TABLE", "TRUNCATE", "DELETE FROM", "GRANT ALL"]
        for query in queries:
            query_upper = query.upper()
            for pattern in dangerous_patterns:
                if pattern in query_upper:
                    checks["sql_injection_risk"] = "elevated"
                    checks["permission_violations"].append(
                        f"Dangerous pattern detected: {pattern}"
                    )

        return checks

    def _assess_compliance(
        self,
        token_usage: dict[str, int],
        cost_analysis: dict[str, Any],
        security_checks: dict[str, Any],
        errors_log: list[dict],
    ) -> dict[str, Any]:
        """Assess overall compliance."""
        issues = []

        # Check token limits (default: 100K tokens per run)
        total_tokens = sum(token_usage.values())
        if total_tokens > 100000:
            issues.append(f"Token usage ({total_tokens}) exceeds recommended limit (100K)")

        # Check cost limits (default: $10 per run)
        estimated_cost = cost_analysis.get("estimated_cost", 0)
        if estimated_cost > 10.0:
            issues.append(f"Estimated cost (${estimated_cost:.4f}) exceeds recommended limit ($10)")

        # Check for security issues
        if security_checks.get("sql_injection_risk") == "elevated":
            issues.append("Elevated SQL injection risk detected")

        # Check error rate
        if len(errors_log) > 5:
            issues.append(f"High error count: {len(errors_log)} errors logged")

        return {
            "compliant": len(issues) == 0,
            "issues": issues,
            "risk_level": "high" if len(issues) > 2 else "medium" if len(issues) > 0 else "low",
        }

    def _generate_recommendations(
        self,
        compliance: dict[str, Any],
        cost_analysis: dict[str, Any],
    ) -> list[str]:
        """Generate governance recommendations."""
        recommendations = []

        if cost_analysis.get("estimated_cost", 0) > 1.0:
            recommendations.append(
                "Consider using a cheaper model for simple tasks to reduce costs"
            )

        if compliance.get("risk_level") == "high":
            recommendations.append(
                "Review security policies and restrict dangerous SQL patterns"
            )

        if not compliance.get("compliant", True):
            recommendations.append(
                f"Address {len(compliance.get('issues', []))} compliance issues before production deployment"
            )

        return recommendations

    def validate_output(self, result: AgentResult) -> bool:
        """Validate that governance analysis was completed."""
        if not result.success or not result.output:
            return False
        return "compliance" in result.output and "cost_analysis" in result.output
