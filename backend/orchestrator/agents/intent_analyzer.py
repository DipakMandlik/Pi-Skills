"""Intent Analyzer Agent — parses user intent and identifies required skills."""

from __future__ import annotations

import logging
import re
from typing import Any

from ..base_agent import AgentResult, BaseAgent
from ..state import PipelineState

logger = logging.getLogger(__name__)

# Skill keyword mapping for intent analysis
SKILL_KEYWORDS = {
    "data-architect": ["schema", "data model", "table design", "fact table", "dimension", "star schema", "data vault", "medallion", "normalize", "denormalize", "ERD", "entity relationship"],
    "sql-writer": ["write a query", "SQL", "SELECT", "JOIN", "CTE", "subquery", "window function", "query to"],
    "query-optimizer": ["optimize", "slow query", "performance", "tune", "explain", "index", "cluster", "query plan"],
    "stored-procedure-writer": ["stored procedure", "CREATE PROCEDURE", "procedure", "automate", "ETL", "pipeline", "BEGIN END"],
    "analytics-engineer": ["dashboard", "report", "metric", "KPI", "aggregation", "rollup", "analytics"],
    "data-quality-engineer": ["data quality", "validation", "test", "check", "constraint", "anomaly", "duplicate"],
    "security-analyst": ["security", "masking", "PII", "access control", "RBAC", "permission", "audit"],
    "cost-optimization": ["cost", "credits", "budget", "expensive", "optimize cost", "warehouse size"],
    "lineage-analyst": ["lineage", "dependency", "upstream", "downstream", "impact", "trace"],
    "semantic-layer-designer": ["semantic", "metric layer", "business logic", "definition", "measure"],
}


class IntentAnalyzerAgent(BaseAgent):
    """Analyzes user input to determine intent, complexity, and required skills."""

    @property
    def name(self) -> str:
        return "intent_analyzer"

    @property
    def dependencies(self) -> list[str]:
        return []

    async def run(self, state: PipelineState) -> AgentResult:
        """Parse user intent from the pipeline input.

        Reads user_intent and selected_skills from state, analyzes complexity,
        and outputs a structured intent analysis.
        """
        user_intent = state.user_intent
        selected_skills = state.selected_skills

        if not user_intent and not selected_skills:
            return AgentResult(
                success=False,
                errors=["No user intent or selected skills provided in state"],
            )

        # Analyze the prompt for complexity
        prompt = user_intent.get("prompt", "")
        complexity = self._analyze_complexity(prompt)

        # Detect additional skills from prompt keywords
        detected_skills = self._detect_skills(prompt)

        # Merge with explicitly selected skills
        all_skills = list(set(selected_skills + detected_skills))

        # Determine the execution path
        execution_path = self._determine_path(all_skills, complexity)

        result = {
            "intent": user_intent,
            "complexity": complexity,
            "selected_skills": selected_skills,
            "detected_skills": detected_skills,
            "all_skills": all_skills,
            "execution_path": execution_path,
            "requires_schema_exploration": self._needs_schema_exploration(all_skills),
        }

        state.update_state(self.name, "outputs", result)
        return AgentResult(success=True, output=result)

    def _analyze_complexity(self, prompt: str) -> str:
        """Analyze prompt complexity."""
        if not prompt:
            return "simple"

        word_count = len(prompt.split())
        char_count = len(prompt)

        has_code = bool(re.search(r'```|def |class |SELECT |FROM |JOIN ', prompt, re.I))
        has_math = bool(re.search(r'\d+\s*[\+\-\*\/]\s*\d+|calculate|solve', prompt, re.I))
        has_reasoning = bool(re.search(r'why|explain|analyze|compare|evaluate|reason', prompt, re.I))
        has_multi_step = bool(re.search(r'then|after that|next|finally|also|and also', prompt, re.I))

        score = 0
        if word_count > 500:
            score += 3
        elif word_count > 200:
            score += 2
        elif word_count > 50:
            score += 1

        if has_code:
            score += 3
        if has_math:
            score += 2
        if has_reasoning:
            score += 2
        if has_multi_step:
            score += 1

        if score <= 2:
            return "simple"
        elif score <= 5:
            return "moderate"
        elif score <= 8:
            return "complex"
        else:
            return "critical"

    def _detect_skills(self, prompt: str) -> list[str]:
        """Detect which skills are needed based on prompt keywords."""
        if not prompt:
            return []

        prompt_lower = prompt.lower()
        detected = []

        for skill, keywords in SKILL_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in prompt_lower:
                    detected.append(skill)
                    break

        return detected

    def _determine_path(self, skills: list[str], complexity: str) -> str:
        """Determine the execution path based on skills and complexity."""
        if "data-architect" in skills:
            return "design_and_build"
        if "sql-writer" in skills or "query-optimizer" in skills:
            return "query_workflow"
        if "stored-procedure-writer" in skills:
            return "procedure_workflow"
        if "analytics-engineer" in skills:
            return "analytics_workflow"
        if complexity in ("complex", "critical"):
            return "full_pipeline"
        return "simple_query"

    def _needs_schema_exploration(self, skills: list[str]) -> bool:
        """Determine if schema exploration is needed."""
        schema_skills = {"data-architect", "sql-writer", "analytics-engineer", "query-optimizer"}
        return bool(set(skills) & schema_skills)
