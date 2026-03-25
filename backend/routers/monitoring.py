from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import AuditLogModel, get_session
from ..schemas.api import (
    AuditLogEntry,
    MonitoringResponse,
    MonitoringSummary,
)

logger = logging.getLogger("backend.monitoring_router")

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("", response_model=MonitoringResponse)
async def get_monitoring(
    request: Request,
    user_id: Optional[str] = Query(None),
    model_id: Optional[str] = Query(None),
    skill_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_session),
):
    current_user = request.state.user

    user_roles = {current_user.role, *(getattr(current_user, "roles", []) or [])}
    normalized_roles = {str(r).upper() for r in user_roles if r}
    is_admin_role = bool(normalized_roles.intersection({"ORG_ADMIN", "SECURITY_ADMIN", "SYSADMIN", "ACCOUNTADMIN", "ADMIN"}))

    filters = []
    if is_admin_role:
        if user_id:
            filters.append(AuditLogModel.user_id == user_id)
    else:
        if user_id and user_id != current_user.user_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "status": 403,
                    "title": "Access Denied",
                    "detail": "Cannot query monitoring data for another user",
                },
            )
        filters.append(AuditLogModel.user_id == current_user.user_id)

    if model_id:
        filters.append(AuditLogModel.model_id == model_id)
    if skill_id:
        filters.append(AuditLogModel.skill_id == skill_id)
    if action:
        filters.append(AuditLogModel.action == action)
    if from_date:
        dt = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
        filters.append(AuditLogModel.timestamp >= dt)
    if to_date:
        dt = datetime.fromisoformat(to_date.replace("Z", "+00:00"))
        filters.append(AuditLogModel.timestamp <= dt)

    where_clause = and_(*filters) if filters else True

    count_q = select(func.count()).select_from(AuditLogModel).where(where_clause)
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    query = (
        select(AuditLogModel)
        .where(where_clause)
        .order_by(AuditLogModel.timestamp.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    rows = result.scalars().all()

    logs = []
    for r in rows:
        logs.append(AuditLogEntry(
            id=str(r.id),
            request_id=str(r.request_id),
            user_id=str(r.user_id) if r.user_id else None,
            skill_id=r.skill_id,
            model_id=r.model_id,
            action=r.action,
            outcome=r.outcome,
            tokens_used=r.tokens_used,
            latency_ms=r.latency_ms,
            timestamp=r.timestamp.isoformat() if r.timestamp else "",
        ))

    exec_filters = [f for f in filters] if filters else []
    exec_filters.append(AuditLogModel.action == "EXEC_SUCCESS")
    exec_q = select(func.coalesce(func.sum(AuditLogModel.tokens_used), 0)).where(and_(*exec_filters) if exec_filters else True)
    exec_result = await db.execute(exec_q)
    total_tokens = exec_result.scalar() or 0

    exec_count_q = select(func.count()).where(and_(*exec_filters) if exec_filters else True)
    exec_count_result = await db.execute(exec_count_q)
    total_execs = exec_count_result.scalar() or 0

    denial_filters = [f for f in filters] if filters else []
    denial_filters.append(AuditLogModel.outcome == "DENIED")
    denial_q = select(func.count()).where(and_(*denial_filters))
    denial_result = await db.execute(denial_q)
    total_denials = denial_result.scalar() or 0

    avg_filters = [f for f in filters] if filters else []
    avg_filters.append(AuditLogModel.latency_ms.isnot(None))
    avg_latency_q = select(func.coalesce(func.avg(AuditLogModel.latency_ms), 0)).where(and_(*avg_filters))
    avg_result = await db.execute(avg_latency_q)
    avg_latency = float(avg_result.scalar() or 0)

    return MonitoringResponse(
        logs=logs,
        total=total,
        page=page,
        page_size=page_size,
        summary=MonitoringSummary(
            total_executions=total_execs,
            total_denials=total_denials,
            total_tokens=total_tokens,
            avg_latency_ms=round(avg_latency, 2),
        ),
    )
