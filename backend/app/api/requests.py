import hashlib
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.core.db import get_session
from app.domain import TRANSITIONS, RequestStatus, Role
from app.models.entities import IdempotencyRecord, RequestEvent, ServiceRequest, User
from app.schemas.requests import RequestCreate, RequestOut, StatusChange

router = APIRouter(prefix="/requests", tags=["requests"])
DISPATCH_ROLES = {Role.DISPATCHER, Role.ORGANIZATION_ADMIN}


@router.post("", response_model=RequestOut, status_code=201)
async def create_request(
    data: RequestCreate,
    idempotency_key: str = Header(min_length=8, max_length=128),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> ServiceRequest:
    if user.role not in {Role.CUSTOMER, Role.DISPATCHER, Role.ORGANIZATION_ADMIN}:
        raise HTTPException(403, "Technicians cannot create customer requests")
    body_hash = hashlib.sha256(data.model_dump_json().encode()).hexdigest()
    existing = await session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.organization_id == user.organization_id,
            IdempotencyRecord.key == idempotency_key,
        )
    )
    if existing:
        if existing.payload_hash != body_hash:
            raise HTTPException(409, "Idempotency key was used with a different payload") from None
        resource = await session.scalar(
            select(ServiceRequest).where(
                ServiceRequest.id == existing.resource_id,
                ServiceRequest.organization_id == user.organization_id,
            )
        )
        if resource is None:
            raise HTTPException(409, "Idempotency record points to a missing resource") from None
        return resource
    item = ServiceRequest(
        organization_id=user.organization_id, customer_id=user.id, **data.model_dump()
    )
    session.add(item)
    try:
        await session.flush()
        session.add(
            IdempotencyRecord(
                organization_id=user.organization_id,
                key=idempotency_key,
                payload_hash=body_hash,
                resource_id=item.id,
            )
        )
        session.add(
            RequestEvent(
                organization_id=user.organization_id,
                request_id=item.id,
                actor_id=user.id,
                to_status=item.status.value,
            )
        )
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await session.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.organization_id == user.organization_id,
                IdempotencyRecord.key == idempotency_key,
            )
        )
        if existing is None:
            raise
        if existing.payload_hash != body_hash:
            raise HTTPException(409, "Idempotency key was used with a different payload") from None
        resource = await session.scalar(
            select(ServiceRequest).where(
                ServiceRequest.id == existing.resource_id,
                ServiceRequest.organization_id == user.organization_id,
            )
        )
        if resource is None:
            raise HTTPException(409, "Idempotency record points to a missing resource") from None
        return resource
    await session.refresh(item)
    return item


@router.get("")
async def list_requests(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=120),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    query = select(ServiceRequest).where(ServiceRequest.organization_id == user.organization_id)
    count_query = (
        select(func.count())
        .select_from(ServiceRequest)
        .where(ServiceRequest.organization_id == user.organization_id)
    )
    if user.role == Role.CUSTOMER:
        query = query.where(ServiceRequest.customer_id == user.id)
        count_query = count_query.where(ServiceRequest.customer_id == user.id)
    if search:
        pattern = f"%{search}%"
        query = query.where(ServiceRequest.title.ilike(pattern))
        count_query = count_query.where(ServiceRequest.title.ilike(pattern))
    total = await session.scalar(count_query) or 0
    rows = (
        await session.scalars(
            query.order_by(ServiceRequest.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return {
        "items": [RequestOut.model_validate(row).model_dump(mode="json") for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.patch("/{request_id}/status", response_model=RequestOut)
async def change_status(
    request_id: UUID,
    change: StatusChange,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> ServiceRequest:
    item = await session.scalar(
        select(ServiceRequest)
        .where(
            ServiceRequest.id == request_id, ServiceRequest.organization_id == user.organization_id
        )
        .with_for_update()
    )
    if item is None:
        raise HTTPException(404, "Request not found")
    if user.role == Role.CUSTOMER:
        raise HTTPException(403, "Role cannot perform this transition")
    # Assignment records are not implemented yet; deny technician mutation until they are.
    if user.role == Role.TECHNICIAN:
        raise HTTPException(403, "Role cannot perform this transition")
    if user.role in DISPATCH_ROLES and item.status not in {
        RequestStatus.SUBMITTED,
        RequestStatus.TRIAGED,
        RequestStatus.SCHEDULED,
        RequestStatus.COMPLETED,
        RequestStatus.REOPENED,
        RequestStatus.BLOCKED,
    }:
        raise HTTPException(403, "Dispatcher cannot perform this transition")
    if user.role in DISPATCH_ROLES and change.status not in {
        RequestStatus.TRIAGED,
        RequestStatus.SCHEDULED,
        RequestStatus.CANCELED,
        RequestStatus.REOPENED,
        RequestStatus.CLOSED,
    }:
        raise HTTPException(403, "Dispatcher cannot perform this transition")
    if change.status not in TRANSITIONS[item.status]:
        raise HTTPException(
            409, f"Invalid transition: {item.status.value} -> {change.status.value}"
        )
    old = item.status
    item.status = change.status
    session.add(
        RequestEvent(
            organization_id=user.organization_id,
            request_id=item.id,
            actor_id=user.id,
            from_status=old.value,
            to_status=change.status.value,
            reason=change.reason,
        )
    )
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/{request_id}", response_model=RequestOut)
async def get_request(
    request_id: UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> ServiceRequest:
    conditions = [
        ServiceRequest.id == request_id,
        ServiceRequest.organization_id == user.organization_id,
    ]
    if user.role == Role.CUSTOMER:
        conditions.append(ServiceRequest.customer_id == user.id)
    item = await session.scalar(select(ServiceRequest).where(*conditions))
    if item is None:
        raise HTTPException(404, "Request not found")
    return item


@router.get("/{request_id}/history")
async def request_history(
    request_id: UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, object]]:
    item = await session.scalar(
        select(ServiceRequest).where(
            ServiceRequest.id == request_id,
            ServiceRequest.organization_id == user.organization_id,
            *([ServiceRequest.customer_id == user.id] if user.role == Role.CUSTOMER else []),
        )
    )
    if item is None:
        raise HTTPException(404, "Request not found")
    events = (
        await session.scalars(
            select(RequestEvent)
            .where(
                RequestEvent.request_id == request_id,
                RequestEvent.organization_id == user.organization_id,
            )
            .order_by(RequestEvent.created_at)
        )
    ).all()
    return [
        {"from": e.from_status, "to": e.to_status, "reason": e.reason, "created_at": e.created_at}
        for e in events
    ]
