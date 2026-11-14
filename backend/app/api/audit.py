from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.core.db import get_session
from app.domain import Role
from app.models.domain_entities import AuditLog
from app.models.entities import User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
async def list_audit_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, object]]:
    if user.role != Role.ORGANIZATION_ADMIN:
        raise HTTPException(403, "Only organization administrators can read audit events")
    rows = (
        await session.scalars(
            select(AuditLog)
            .where(AuditLog.organization_id == user.organization_id)
            .order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return [
        {
            "id": str(row.id),
            "actor_id": str(row.actor_id) if row.actor_id else None,
            "action": row.action,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "before": row.before,
            "after": row.after,
            "created_at": row.created_at.isoformat()
            if isinstance(row.created_at, datetime)
            else None,
        }
        for row in rows
    ]
