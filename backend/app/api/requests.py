import hashlib
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.core.db import get_session
from app.domain import TRANSITIONS, AssignmentStatus, EstimateStatus, RequestStatus, Role
from app.models.domain_entities import (
    Asset,
    Assignment,
    AssignmentEvent,
    AuditLog,
    Category,
    Estimate,
    Property,
    Technician,
)
from app.models.entities import IdempotencyRecord, RequestEvent, ServiceRequest, User
from app.schemas.requests import RequestCreate, RequestOut, StatusChange
from app.services.notifications import enqueue_notifications

router = APIRouter(prefix="/requests", tags=["requests"])
DISPATCH_ROLES = {Role.DISPATCHER, Role.ORGANIZATION_ADMIN}


def _technician_request_ids(user: User):
    return (
        select(Assignment.request_id)
        .join(Technician, Technician.id == Assignment.technician_id)
        .where(
            Assignment.organization_id == user.organization_id,
            Assignment.status.in_(
                {AssignmentStatus.OFFERED, AssignmentStatus.ACCEPTED, AssignmentStatus.COMPLETED}
            ),
            Technician.organization_id == user.organization_id,
            Technician.user_id == user.id,
            Technician.active.is_(True),
        )
    )


@router.post("", response_model=RequestOut, status_code=201)
async def create_request(
    data: RequestCreate,
    idempotency_key: str = Header(min_length=8, max_length=128),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> ServiceRequest:
    if user.role not in {Role.CUSTOMER, Role.DISPATCHER, Role.ORGANIZATION_ADMIN}:
        raise HTTPException(403, "Technicians cannot create customer requests")
    if data.property_id and not await session.scalar(
        select(Property.id).where(
            Property.id == data.property_id,
            Property.organization_id == user.organization_id,
            Property.active.is_(True),
        )
    ):
        raise HTTPException(404, "Property not found")
    if data.category_id and not await session.scalar(
        select(Category.id).where(
            Category.id == data.category_id,
            Category.organization_id == user.organization_id,
            Category.active.is_(True),
        )
    ):
        raise HTTPException(404, "Category not found")
    if data.asset_id:
        asset = await session.scalar(
            select(Asset).where(
                Asset.id == data.asset_id,
                Asset.organization_id == user.organization_id,
                Asset.active.is_(True),
            )
        )
        if asset is None:
            raise HTTPException(404, "Equipment not found")
        if data.property_id and data.property_id != asset.property_id:
            raise HTTPException(422, "Equipment does not belong to the selected property")
        data.property_id = asset.property_id
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
        dispatchers = (
            await session.scalars(
                select(User.id).where(
                    User.organization_id == user.organization_id,
                    User.active.is_(True),
                    User.role.in_({Role.DISPATCHER, Role.ORGANIZATION_ADMIN}),
                )
            )
        ).all()
        enqueue_notifications(
            session,
            organization_id=user.organization_id,
            user_ids=dispatchers,
            event_key=f"request.created:{item.id}",
            title="New service request",
            body=item.title,
            request_id=item.id,
        )
        session.add(
            AuditLog(
                organization_id=user.organization_id,
                actor_id=user.id,
                action="request.created",
                resource_type="service_request",
                resource_id=str(item.id),
                after={"status": item.status.value},
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
    elif user.role == Role.TECHNICIAN:
        technician_requests = _technician_request_ids(user)
        query = query.where(ServiceRequest.id.in_(technician_requests))
        count_query = count_query.where(ServiceRequest.id.in_(technician_requests))
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
    request_conditions = [
        ServiceRequest.id == request_id,
        ServiceRequest.organization_id == user.organization_id,
    ]
    if user.role == Role.CUSTOMER:
        request_conditions.append(ServiceRequest.customer_id == user.id)
    item = await session.scalar(select(ServiceRequest).where(*request_conditions).with_for_update())
    if item is None:
        raise HTTPException(404, "Request not found")
    if change.status == RequestStatus.IN_PROGRESS:
        waiting_estimate = await session.scalar(
            select(Estimate.id)
            .where(
                Estimate.organization_id == user.organization_id,
                Estimate.request_id == item.id,
                Estimate.status == EstimateStatus.AWAITING_APPROVAL,
            )
            .limit(1)
        )
        if waiting_estimate is not None:
            raise HTTPException(409, "Work cannot start while an estimate awaits approval")
    if user.role == Role.CUSTOMER:
        raise HTTPException(403, "Role cannot perform this transition")
    active_assignment = None
    if user.role == Role.TECHNICIAN:
        if change.status not in {
            RequestStatus.IN_PROGRESS,
            RequestStatus.BLOCKED,
            RequestStatus.COMPLETED,
        }:
            raise HTTPException(403, "Technician cannot perform this transition")
        active_assignment = await session.scalar(
            select(Assignment)
            .join(Technician, Technician.id == Assignment.technician_id)
            .where(
                Assignment.organization_id == user.organization_id,
                Assignment.request_id == item.id,
                Assignment.status == AssignmentStatus.ACCEPTED,
                Technician.organization_id == user.organization_id,
                Technician.user_id == user.id,
                Technician.active.is_(True),
            )
            .with_for_update()
        )
        if active_assignment is None:
            raise HTTPException(403, "Technician has no accepted assignment for this request")
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
    if active_assignment and change.status == RequestStatus.COMPLETED:
        old_assignment_status = active_assignment.status
        active_assignment.status = AssignmentStatus.COMPLETED
        session.add(
            AssignmentEvent(
                organization_id=user.organization_id,
                assignment_id=active_assignment.id,
                actor_id=user.id,
                from_status=old_assignment_status.value,
                to_status=active_assignment.status.value,
            )
        )
    status_event = RequestEvent(
        organization_id=user.organization_id,
        request_id=item.id,
        actor_id=user.id,
        from_status=old.value,
        to_status=change.status.value,
        reason=change.reason,
    )
    session.add(status_event)
    await session.flush()
    session.add(
        AuditLog(
            organization_id=user.organization_id,
            actor_id=user.id,
            action="request.status_changed",
            resource_type="service_request",
            resource_id=str(item.id),
            before={"status": old.value},
            after={"status": change.status.value, "reason": change.reason},
        )
    )
    enqueue_notifications(
        session,
        organization_id=user.organization_id,
        user_ids=[item.customer_id],
        event_key=f"request.status:{status_event.id}",
        title="Request status changed",
        body=change.status.value,
        request_id=item.id,
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
    elif user.role == Role.TECHNICIAN:
        conditions.append(ServiceRequest.id.in_(_technician_request_ids(user)))
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
            *(
                [ServiceRequest.id.in_(_technician_request_ids(user))]
                if user.role == Role.TECHNICIAN
                else []
            ),
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
