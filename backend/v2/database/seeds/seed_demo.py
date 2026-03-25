from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, text

from backend.v2.config.settings import Settings
from backend.v2.database.client import (
    OrganizationModel,
    SkillAssignmentModel,
    SkillModel,
    SkillVersionModel,
    TeamMemberModel,
    TeamModel,
    UserModel,
    _session_factory,
)
from backend.v2.modules.auth.service import hash_password
from backend.v2.shared.logger import get_logger

logger = get_logger("seeds")


async def seed_demo(settings: Settings):
    if _session_factory is None:
        logger.warning("No session factory, skipping seed")
        return

    async with _session_factory() as db:
        existing = await db.execute(select(OrganizationModel).limit(1))
        if existing.scalar_one_or_none() is not None:
            logger.info("Demo data already exists, skipping seed")
            return

        org_id = str(uuid4())
        org = OrganizationModel(id=org_id, name="Demo Organization", slug="demo-org", plan="free", settings={})
        db.add(org)

        pw = hash_password
        users = [
            {"id": str(uuid4()), "email": "owner@demo.local", "name": "Platform Owner", "role": "OWNER", "password": "owner1234"},
            {"id": str(uuid4()), "email": "admin@demo.local", "name": "Team Admin", "role": "ADMIN", "password": "admin1234"},
            {"id": str(uuid4()), "email": "member@demo.local", "name": "Team Member", "role": "MEMBER", "password": "member1234"},
            {"id": str(uuid4()), "email": "viewer@demo.local", "name": "Viewer", "role": "VIEWER", "password": "viewer1234"},
        ]

        user_ids = []
        for u in users:
            user = UserModel(id=u["id"], org_id=org_id, email=u["email"], name=u["name"], role=u["role"], status="active", password_hash=pw(u["password"]))
            db.add(user)
            user_ids.append(u["id"])

        owner_id = user_ids[0]
        admin_id = user_ids[1]
        member_id = user_ids[2]
        viewer_id = user_ids[3]

        team_id = str(uuid4())
        team = TeamModel(id=team_id, org_id=org_id, name="Engineering", description="Core engineering team")
        db.add(team)
        db.add(TeamMemberModel(id=str(uuid4()), team_id=team_id, user_id=admin_id))
        db.add(TeamMemberModel(id=str(uuid4()), team_id=team_id, user_id=member_id))

        skills = [
            {"id": str(uuid4()), "name": "Code Reviewer", "description": "Automated code review and suggestions", "content": "Review the provided code for best practices, potential bugs, and performance improvements.", "category": "development"},
            {"id": str(uuid4()), "name": "SQL Optimizer", "description": "Analyze and optimize SQL queries", "content": "Analyze the SQL query and suggest optimizations for better performance.", "category": "database"},
            {"id": str(uuid4()), "name": "Data Analyst", "description": "Generate insights from datasets", "content": "Analyze the provided dataset and generate meaningful insights and visualizations.", "category": "analytics"},
            {"id": str(uuid4()), "name": "Documentation Writer", "description": "Create technical documentation", "content": "Generate clear, comprehensive technical documentation for the provided code or API.", "category": "documentation"},
        ]

        now = datetime.now(UTC)
        for s in skills:
            skill = SkillModel(id=s["id"], org_id=org_id, name=s["name"], description=s["description"], content=s["content"], category=s["category"], status="active", created_by=owner_id, version=1, created_at=now, updated_at=now)
            db.add(skill)
            db.add(SkillVersionModel(id=str(uuid4()), skill_id=s["id"], content=s["content"], version=1, created_by=owner_id, created_at=now))

        db.add(SkillAssignmentModel(id=str(uuid4()), skill_id=skills[0]["id"], assignee_type="user", assignee_id=member_id, assigned_by=admin_id, assigned_at=now))
        db.add(SkillAssignmentModel(id=str(uuid4()), skill_id=skills[1]["id"], assignee_type="user", assignee_id=member_id, assigned_by=admin_id, assigned_at=now))
        db.add(SkillAssignmentModel(id=str(uuid4()), skill_id=skills[2]["id"], assignee_type="team", assignee_id=team_id, assigned_by=admin_id, assigned_at=now))

        await db.commit()
        logger.info("Demo data seeded: 1 org, 4 users, 1 team, 4 skills, 3 assignments")
