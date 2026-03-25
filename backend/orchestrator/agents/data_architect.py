"""Data Architect Agent — designs data models, schemas, and DDL."""

from __future__ import annotations

import logging
from typing import Any

from ..base_agent import AgentResult, BaseAgent
from ..state import PipelineState

logger = logging.getLogger(__name__)


class DataArchitectAgent(BaseAgent):
    """Designs data models and produces DDL based on user intent and schema inventory.

    Reads intent analysis and schema exploration results from state,
    then produces structured data model designs including table definitions,
    relationships, and optionally full DDL statements.
    """

    @property
    def name(self) -> str:
        return "data_architect"

    @property
    def dependencies(self) -> list[str]:
        return ["intent_analyzer", "schema_explorer"]

    async def run(self, state: PipelineState) -> AgentResult:
        """Design data model based on intent and schema exploration.

        Reads outputs from intent_analyzer and schema_explorer,
        produces a structured data model design.
        """
        intent_output = state.outputs.get("intent_analyzer")
        schema_output = state.outputs.get("schema_explorer")

        if not intent_output:
            return AgentResult(
                success=False,
                errors=["No intent analysis available"],
            )

        user_intent = state.user_intent
        prompt = user_intent.get("prompt", "")
        complexity = intent_output.get("complexity", "simple")

        # Determine modeling paradigm
        paradigm = self._select_paradigm(prompt, complexity)

        # Design the model
        model_design = {
            "paradigm": paradigm,
            "entities": self._design_entities(prompt, paradigm),
            "relationships": self._design_relationships(prompt, paradigm),
            "naming_convention": "snake_case",
            "scd_strategy": self._determine_scd(prompt),
            "ddl_statements": self._generate_ddl(prompt, paradigm),
            "source_databases": schema_output.get("databases", []) if schema_output else [],
        }

        state.update_state(self.name, "outputs", model_design)
        return AgentResult(success=True, output=model_design)

    def _select_paradigm(self, prompt: str, complexity: str) -> str:
        """Select the appropriate modeling paradigm."""
        prompt_lower = prompt.lower()
        if any(kw in prompt_lower for kw in ["analytics", "dashboard", "report", "BI"]):
            return "dimensional"
        if any(kw in prompt_lower for kw in ["data vault", "hub", "satellite", "audit trail"]):
            return "data_vault"
        if any(kw in prompt_lower for kw in ["bronze", "silver", "gold", "medallion", "lakehouse"]):
            return "medallion"
        if any(kw in prompt_lower for kw in ["transaction", "OLTP", "operational"]):
            return "3NF"
        return "dimensional"

    def _design_entities(self, prompt: str, paradigm: str) -> list[dict[str, Any]]:
        """Design entities based on prompt and paradigm."""
        entities = []
        prompt_lower = prompt.lower()

        if paradigm == "dimensional":
            if any(kw in prompt_lower for kw in ["order", "sale", "purchase"]):
                entities = [
                    {"name": "fct_orders", "type": "fact", "grain": "one row per order line item"},
                    {"name": "dim_customer", "type": "dimension", "scd": "Type 2"},
                    {"name": "dim_product", "type": "dimension", "scd": "Type 1"},
                    {"name": "dim_date", "type": "dimension", "scd": "Type 0"},
                ]
            elif any(kw in prompt_lower for kw in ["user", "session", "web", "page"]):
                entities = [
                    {"name": "fct_page_views", "type": "fact", "grain": "one row per page view"},
                    {"name": "dim_user", "type": "dimension", "scd": "Type 2"},
                    {"name": "dim_page", "type": "dimension", "scd": "Type 1"},
                    {"name": "dim_date", "type": "dimension", "scd": "Type 0"},
                ]
            else:
                # Default dimensional model for any other prompt
                entities = [
                    {"name": "fct_events", "type": "fact", "grain": "one row per event"},
                    {"name": "dim_entity", "type": "dimension", "scd": "Type 1"},
                    {"name": "dim_date", "type": "dimension", "scd": "Type 0"},
                ]
        elif paradigm == "data_vault":
            entities = [
                {"name": "hub_customer", "type": "hub", "business_key": "customer_id"},
                {"name": "hub_order", "type": "hub", "business_key": "order_id"},
                {"name": "lnk_order_customer", "type": "link"},
                {"name": "sat_customer_crm", "type": "satellite", "source": "CRM"},
            ]
        elif paradigm == "medallion":
            entities = [
                {"name": "bronze_orders", "type": "bronze", "purpose": "Raw ingestion"},
                {"name": "silver_orders", "type": "silver", "purpose": "Cleansed and typed"},
                {"name": "gold_order_metrics", "type": "gold", "purpose": "Business aggregations"},
            ]
        else:
            entities = [
                {"name": "orders", "type": "table", "normalization": "3NF"},
                {"name": "customers", "type": "table", "normalization": "3NF"},
                {"name": "products", "type": "table", "normalization": "3NF"},
            ]

        return entities

    def _design_relationships(self, prompt: str, paradigm: str) -> list[dict[str, str]]:
        """Design relationships between entities."""
        if paradigm == "dimensional":
            return [
                {"from": "fct_orders", "to": "dim_customer", "type": "many-to-one", "fk": "customer_sk"},
                {"from": "fct_orders", "to": "dim_product", "type": "many-to-one", "fk": "product_sk"},
                {"from": "fct_orders", "to": "dim_date", "type": "many-to-one", "fk": "order_date_sk"},
            ]
        elif paradigm == "data_vault":
            return [
                {"from": "lnk_order_customer", "to": "hub_order", "type": "many-to-one", "fk": "order_hk"},
                {"from": "lnk_order_customer", "to": "hub_customer", "type": "many-to-one", "fk": "customer_hk"},
                {"from": "sat_customer_crm", "to": "hub_customer", "type": "many-to-one", "fk": "customer_hk"},
            ]
        return []

    def _determine_scd(self, prompt: str) -> str:
        """Determine slowly changing dimension strategy."""
        prompt_lower = prompt.lower()
        if "history" in prompt_lower or "track changes" in prompt_lower:
            return "Type 2"
        if "previous" in prompt_lower or "prior" in prompt_lower:
            return "Type 3"
        return "Type 1"

    def _generate_ddl(self, prompt: str, paradigm: str) -> list[str]:
        """Generate DDL statements based on paradigm."""
        if paradigm == "dimensional":
            return [
                "CREATE TABLE IF NOT EXISTS dim_customer (\n"
                "    customer_sk NUMBER NOT NULL AUTOINCREMENT PRIMARY KEY,\n"
                "    customer_id VARCHAR(50) NOT NULL UNIQUE,\n"
                "    full_name VARCHAR(200) NOT NULL,\n"
                "    email VARCHAR(200),\n"
                "    dw_created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),\n"
                "    dw_updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP()\n"
                ");",
                "CREATE TABLE IF NOT EXISTS fct_orders (\n"
                "    order_sk NUMBER NOT NULL AUTOINCREMENT PRIMARY KEY,\n"
                "    order_date_sk NUMBER NOT NULL REFERENCES dim_date(date_sk),\n"
                "    customer_sk NUMBER NOT NULL REFERENCES dim_customer(customer_sk),\n"
                "    total_amount NUMBER(12,2) NOT NULL,\n"
                "    etl_loaded_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP()\n"
                ");",
            ]
        return ["-- DDL generation not yet implemented for this paradigm"]

    def validate_output(self, result: AgentResult) -> bool:
        """Validate that the data model design is complete."""
        if not result.success or not result.output:
            return False
        entities = result.output.get("entities", [])
        return len(entities) > 0 and "paradigm" in result.output
