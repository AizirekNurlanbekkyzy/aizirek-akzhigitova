from collections.abc import Iterable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain_entities import Notification


def enqueue_notifications(
    session: AsyncSession,
    *,
    organization_id: UUID,
    user_ids: Iterable[UUID],
    event_key: str,
    title: str,
    body: str,
    request_id: UUID | None = None,
) -> None:
    session.add_all(
        [
            Notification(
                organization_id=organization_id,
                user_id=user_id,
                request_id=request_id,
                event_key=event_key,
                title=title,
                body=body,
            )
            for user_id in set(user_ids)
        ]
    )
