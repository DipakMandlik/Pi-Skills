from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import ModelPermissionModel, RegisteredModelModel, get_session
from ..schemas.api import (
    ModelAssignRequest,
    ModelAssignResponse,
    ModelListItem,
    ModelRevokeRequest,
    ModelRevokeResponse,
    ModelAccessInfo,
    ModelsListResponse,
)
from ..services.permission_service import invalidate_user_permissions

logger = logging.getLogger("backend.models_router")

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=ModelsListResponse)
async def list_models(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    user = request.state.user

    all_models = await db.execute(
        select(RegisteredModelModel).where(RegisteredModelModel.is_available == True)
    )
    all_models_list = all_models.scalars().all()

    if user.role == "admin":
        return ModelsListResponse(
            models=[
                ModelListItem(
                    model_id=m.model_id,
                    display_name=m.display_name,
                    provider=m.provider,
                    tier=m.tier or "standard",
                    is_available=m.is_available,
                    access=None,
                )
                for m in all_models_list
            ]
        )

    perm_result = await db.execute(
        select(ModelPermissionModel).where(
            ModelPermissionModel.user_id == user.user_id,
            ModelPermissionModel.is_active == True,
        )
    )
    perms = {p.model_id: p for p in perm_result.scalars().all()}

    models = []
    for m in all_models_list:
        if m.model_id not in perms:
            continue
        p = perms[m.model_id]
        models.append(ModelListItem(
            model_id=m.model_id,
            display_name=m.display_name,
            provider=m.provider,
            tier=m.tier or "standard",
            is_available=m.is_available,
            access=ModelAccessInfo(
                granted_at=p.granted_at.isoformat() if p.granted_at else "",
                expires_at=p.expires_at.isoformat() if p.expires_at else None,
                is_active=p.is_active,
            ),
        ))

    return ModelsListResponse(models=models)


@router.post("/assign", response_model=ModelAssignResponse)
async def assign_model(
    body: ModelAssignRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    user = request.state.user
    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail={"status": 403, "title": "Access Denied", "detail": "Admin role required"},
        )

    model_check = await db.execute(
        select(RegisteredModelModel).where(RegisteredModelModel.model_id == body.model_id)
    )
    if model_check.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=400,
            detail={"status": 400, "title": "Bad Request", "detail": f"Unknown model: {body.model_id}"},
        )

    existing = await db.execute(
        select(ModelPermissionModel).where(
            ModelPermissionModel.user_id == body.user_id,
            ModelPermissionModel.model_id == body.model_id,
            ModelPermissionModel.is_active == True,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail={"status": 409, "title": "Conflict", "detail": "Model already assigned to this user"},
        )

    now = datetime.now(timezone.utc)
    expires_at = None
    if body.expires_at:
        expires_at = datetime.fromisoformat(body.expires_at.replace("Z", "+00:00"))

    perm = ModelPermissionModel(
        id=str(uuid4()),
        user_id=body.user_id,
        model_id=body.model_id,
        granted_by=user.user_id,
        granted_at=now,
        expires_at=expires_at,
        is_active=True,
        notes=body.notes,
    )
    db.add(perm)
    await db.commit()
    await db.refresh(perm)

    await invalidate_user_permissions(body.user_id)

    return ModelAssignResponse(
        permission_id=str(perm.id),
        user_id=str(perm.user_id),
        model_id=perm.model_id,
        granted_at=perm.granted_at.isoformat(),
        expires_at=perm.expires_at.isoformat() if perm.expires_at else None,
        granted_by=str(perm.granted_by),
    )


@router.post("/revoke", response_model=ModelRevokeResponse)
async def revoke_model(
    body: ModelRevokeRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    user = request.state.user
    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail={"status": 403, "title": "Access Denied", "detail": "Admin role required"},
        )

    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(ModelPermissionModel)
        .where(
            ModelPermissionModel.user_id == body.user_id,
            ModelPermissionModel.model_id == body.model_id,
            ModelPermissionModel.is_active == True,
        )
        .values(
            is_active=False,
            revoked_by=user.user_id,
            revoked_at=now,
        )
    )
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail={"status": 404, "title": "Not Found", "detail": "No active permission found"},
        )

    await invalidate_user_permissions(body.user_id)

    return ModelRevokeResponse(
        revoked=True,
        effective_immediately=True,
        cache_invalidated=True,
    )
