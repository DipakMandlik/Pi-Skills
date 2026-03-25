"""
Governance Policy Engine - Enforces configurable governance policies
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import Base, GUID
from sqlalchemy import Column, String, Boolean, DateTime, Text, func

logger = logging.getLogger("backend.policy_engine")


class GovernancePolicyModel(Base):
    __tablename__ = "governance_policies"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid4()))
    policy_name = Column(String(255), nullable=False, unique=True)
    policy_type = Column(String(100), nullable=False)
    description = Column(Text)
    conditions = Column(Text, default="{}")
    actions = Column(Text, default="{}")
    priority = Column(String(50), default="standard")
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


POLICY_TYPES = {
    "token_limit": "Enforce token consumption limits",
    "model_access": "Control model access by role/plan",
    "rate_limit": "Enforce request rate limits",
    "cost_budget": "Enforce cost budget limits",
    "time_restriction": "Restrict access to specific time windows",
    "ip_restriction": "Restrict access by IP range",
    "content_filter": "Filter content in prompts/responses",
    "session_limit": "Enforce session duration limits",
}


class PolicyEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_policy(
        self,
        policy_name: str,
        policy_type: str,
        description: str = "",
        conditions: Optional[dict] = None,
        actions: Optional[dict] = None,
        priority: str = "standard",
        enabled: bool = True,
    ) -> dict:
        if policy_type not in POLICY_TYPES:
            raise ValueError(f"Invalid policy type: {policy_type}. Allowed: {list(POLICY_TYPES.keys())}")

        existing = await self.db.execute(
            select(GovernancePolicyModel).where(
                GovernancePolicyModel.policy_name == policy_name
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ValueError(f"Policy '{policy_name}' already exists")

        import json
        policy = GovernancePolicyModel(
            policy_name=policy_name,
            policy_type=policy_type,
            description=description,
            conditions=json.dumps(conditions or {}),
            actions=json.dumps(actions or {}),
            priority=priority,
            enabled=enabled,
        )
        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)

        return self._serialize_policy(policy)

    async def update_policy(
        self,
        policy_name: str,
        description: Optional[str] = None,
        conditions: Optional[dict] = None,
        actions: Optional[dict] = None,
        priority: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> dict:
        result = await self.db.execute(
            select(GovernancePolicyModel).where(
                GovernancePolicyModel.policy_name == policy_name
            )
        )
        policy = result.scalar_one_or_none()
        if policy is None:
            raise ValueError(f"Policy '{policy_name}' not found")

        import json
        if description is not None:
            policy.description = description
        if conditions is not None:
            policy.conditions = json.dumps(conditions)
        if actions is not None:
            policy.actions = json.dumps(actions)
        if priority is not None:
            policy.priority = priority
        if enabled is not None:
            policy.enabled = enabled

        policy.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

        return self._serialize_policy(policy)

    async def delete_policy(self, policy_name: str) -> dict:
        result = await self.db.execute(
            select(GovernancePolicyModel).where(
                GovernancePolicyModel.policy_name == policy_name
            )
        )
        policy = result.scalar_one_or_none()
        if policy is None:
            raise ValueError(f"Policy '{policy_name}' not found")

        await self.db.delete(policy)
        await self.db.commit()

        return {"policy_name": policy_name, "deleted": True}

    async def list_policies(
        self,
        policy_type: Optional[str] = None,
        enabled_only: bool = False,
    ) -> list[dict]:
        query = select(GovernancePolicyModel)

        if policy_type:
            query = query.where(GovernancePolicyModel.policy_type == policy_type)
        if enabled_only:
            query = query.where(GovernancePolicyModel.enabled == True)

        query = query.order_by(GovernancePolicyModel.priority.desc())

        result = await self.db.execute(query)
        policies = result.scalars().all()

        return [self._serialize_policy(p) for p in policies]

    async def get_policy(self, policy_name: str) -> Optional[dict]:
        result = await self.db.execute(
            select(GovernancePolicyModel).where(
                GovernancePolicyModel.policy_name == policy_name
            )
        )
        policy = result.scalar_one_or_none()
        if policy is None:
            return None
        return self._serialize_policy(policy)

    async def evaluate_request(
        self,
        user_id: str,
        user_role: str,
        model_id: str,
        task_type: str,
        estimated_tokens: int,
        context: Optional[dict] = None,
    ) -> dict:
        import json

        policies = await self.list_policies(enabled_only=True)
        violations = []
        warnings = []
        allowed = True

        for policy in policies:
            conditions = json.loads(policy["conditions"]) if isinstance(policy["conditions"], str) else policy["conditions"]
            actions = json.loads(policy["actions"]) if isinstance(policy["actions"], str) else policy["actions"]

            if policy["policy_type"] == "token_limit":
                max_tokens = conditions.get("max_tokens", 0)
                if max_tokens > 0 and estimated_tokens > max_tokens:
                    violations.append({
                        "policy": policy["policy_name"],
                        "type": "token_limit",
                        "message": f"Estimated tokens ({estimated_tokens}) exceed limit ({max_tokens})",
                    })
                    if actions.get("deny", False):
                        allowed = False

            elif policy["policy_type"] == "model_access":
                denied_models = conditions.get("denied_models", [])
                if model_id in denied_models:
                    violations.append({
                        "policy": policy["policy_name"],
                        "type": "model_access",
                        "message": f"Model '{model_id}' is denied by policy",
                    })
                    if actions.get("deny", False):
                        allowed = False

                denied_roles = conditions.get("denied_roles", [])
                if user_role in denied_roles:
                    violations.append({
                        "policy": policy["policy_name"],
                        "type": "model_access",
                        "message": f"Role '{user_role}' is denied by policy",
                    })
                    if actions.get("deny", False):
                        allowed = False

            elif policy["policy_type"] == "time_restriction":
                restricted_hours = conditions.get("restricted_hours", [])
                current_hour = datetime.now(timezone.utc).hour
                if current_hour in restricted_hours:
                    warnings.append({
                        "policy": policy["policy_name"],
                        "type": "time_restriction",
                        "message": f"Access during restricted hour {current_hour}",
                    })
                    if actions.get("deny", False):
                        allowed = False

            elif policy["policy_type"] == "content_filter":
                blocked_patterns = conditions.get("blocked_patterns", [])
                if context and "prompt" in context:
                    prompt = context["prompt"].lower()
                    for pattern in blocked_patterns:
                        if pattern.lower() in prompt:
                            violations.append({
                                "policy": policy["policy_name"],
                                "type": "content_filter",
                                "message": f"Blocked content pattern detected",
                            })
                            if actions.get("deny", False):
                                allowed = False
                            break

        return {
            "allowed": allowed,
            "violations": violations,
            "warnings": warnings,
            "policies_evaluated": len(policies),
        }

    def _serialize_policy(self, policy) -> dict:
        import json
        return {
            "id": str(policy.id),
            "policy_name": policy.policy_name,
            "policy_type": policy.policy_type,
            "description": policy.description,
            "conditions": json.loads(policy.conditions) if policy.conditions else {},
            "actions": json.loads(policy.actions) if policy.actions else {},
            "priority": policy.priority,
            "enabled": policy.enabled,
            "created_at": policy.created_at.isoformat() if policy.created_at else None,
            "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
        }

    @staticmethod
    def get_policy_types() -> dict:
        return POLICY_TYPES
