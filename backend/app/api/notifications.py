from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.core.db import get_session
from app.models.domain_entities import Notification
from app.models.entities import User
from app.schemas.notifications import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    unread_only: bool = False,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    conditions = [
        Notification.organization_id == user.organization_id,
        Notification.user_id == user.id,
    ]
    if unread_only:
        conditions.append(Notification.read_at.is_(None))
    rows = (
        await session.scalars(
            select(Notification)
            .where(*conditions)
            .order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return {
        "items": [NotificationOut.model_validate(row).model_dump(mode="json") for row in rows],
        "page": page,
        "page_size": page_size,
    }


@router.patch("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(
    notification_id: UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Notification:
    notification = await session.scalar(
        select(Notification)
        .where(
            Notification.id == notification_id,
            Notification.organization_id == user.organization_id,
            Notification.user_id == user.id,
        )
        .with_for_update()
    )
    if notification is None:
        raise HTTPException(404, "Notification not found")
    notification.read_at = notification.read_at or datetime.now(UTC)
    await session.commit()
    await session.refresh(notification)
    return notification
