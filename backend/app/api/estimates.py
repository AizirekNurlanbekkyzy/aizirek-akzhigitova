from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.core.db import get_session
from app.domain import AssignmentStatus, EstimateStatus, Role
from app.models.domain_entities import (
    Assignment,
    AuditLog,
    Estimate,
    EstimateEvent,
    EstimateLine,
    InventoryItem,
    Technician,
)
from app.models.entities import IdempotencyRecord, ServiceRequest, User
from app.schemas.estimates import (
    EstimateDecision,
    EstimateDraft,
    EstimateEventOut,
    EstimateLineOut,
    EstimateOut,
)
from app.services.notifications import enqueue_notifications

router = APIRouter(tags=["estimates"])
MANAGER_ROLES = {Role.DISPATCHER, Role.ORGANIZATION_ADMIN}


async def _request_for_user(request_id: UUID, user: User, session: AsyncSession) -> ServiceRequest:
    conditions = [
        ServiceRequest.id == request_id,
        ServiceRequest.organization_id == user.organization_id,
    ]
    if user.role == Role.CUSTOMER:
        conditions.append(ServiceRequest.customer_id == user.id)
    elif user.role == Role.TECHNICIAN:
        conditions.append(
            ServiceRequest.id.in_(
                select(Assignment.request_id)
                .join(Technician, Technician.id == Assignment.technician_id)
                .where(
                    Assignment.organization_id == user.organization_id,
                    Assignment.status.in_(
                        {
                            AssignmentStatus.OFFERED,
                            AssignmentStatus.ACCEPTED,
                            AssignmentStatus.COMPLETED,
                        }
                    ),
                    Technician.organization_id == user.organization_id,
                    Technician.user_id == user.id,
                    Technician.active.is_(True),
                )
            )
        )
    request = await session.scalar(select(ServiceRequest).where(*conditions))
    if request is None:
        raise HTTPException(404, "Request not found")
    return request


async def _response(session: AsyncSession, estimate: Estimate) -> EstimateOut:
    lines = (
        await session.scalars(
            select(EstimateLine)
            .where(
                EstimateLine.estimate_id == estimate.id,
                EstimateLine.organization_id == estimate.organization_id,
            )
            .order_by(EstimateLine.id)
        )
    ).all()
    return EstimateOut(
        id=estimate.id,
        request_id=estimate.request_id,
        version=estimate.version,
        previous_version_id=estimate.previous_version_id,
        status=estimate.status,
        total_tyiyn=estimate.total_tyiyn,
        comment=estimate.comment,
        created_at=estimate.created_at,
        decided_at=estimate.decided_at,
        lines=[EstimateLineOut.model_validate(line) for line in lines],
    )


async def _replace_lines(session: AsyncSession, estimate: Estimate, data: EstimateDraft) -> None:
    item_ids = {line.inventory_item_id for line in data.lines if line.inventory_item_id}
    if item_ids:
        found = set(
            (
                await session.scalars(
                    select(InventoryItem.id).where(
                        InventoryItem.id.in_(item_ids),
                        InventoryItem.organization_id == estimate.organization_id,
                        InventoryItem.active.is_(True),
                    )
                )
            ).all()
        )
        if found != item_ids:
            raise HTTPException(404, "Estimate material not found")
    total = sum(
        (line.quantity * line.unit_price_tyiyn).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        for line in data.lines
    )
    from sqlalchemy import delete

    await session.execute(delete(EstimateLine).where(EstimateLine.estimate_id == estimate.id))
    session.add_all(
        [
            EstimateLine(
                organization_id=estimate.organization_id,
                estimate_id=estimate.id,
                **line.model_dump(),
            )
            for line in data.lines
        ]
    )
    estimate.total_tyiyn = int(total)
    estimate.comment = data.comment


def _event(
    estimate: Estimate,
    user: User,
    old_status: EstimateStatus | None,
    comment: str | None,
) -> EstimateEvent:
    return EstimateEvent(
        organization_id=user.organization_id,
        estimate_id=estimate.id,
        actor_id=user.id,
        from_status=old_status.value if old_status else None,
        to_status=estimate.status.value,
        comment=comment,
    )


@router.post("/requests/{request_id}/estimates", response_model=EstimateOut, status_code=201)
async def create_estimate(
    request_id: UUID,
    data: EstimateDraft,
    idempotency_key: str = Header(min_length=8, max_length=128),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> EstimateOut:
    if user.role not in MANAGER_ROLES:
        raise HTTPException(403, "Role cannot create estimates")
    request = await _request_for_user(request_id, user, session)
    payload_hash = hashlib.sha256(
        f"estimate.create:{request_id}:{data.model_dump_json()}".encode()
    ).hexdigest()
    existing = await session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.organization_id == user.organization_id,
            IdempotencyRecord.key == idempotency_key,
        )
    )
    if existing:
        if existing.payload_hash != payload_hash:
            raise HTTPException(409, "Idempotency key was used with a different payload")
        saved = await session.scalar(
            select(Estimate).where(
                Estimate.id == existing.resource_id,
                Estimate.organization_id == user.organization_id,
            )
        )
        if saved is None:
            raise HTTPException(409, "Estimate idempotency record has no matching version")
        return await _response(session, saved)

    previous = await session.scalar(
        select(Estimate)
        .where(
            Estimate.organization_id == user.organization_id,
            Estimate.request_id == request.id,
        )
        .order_by(Estimate.version.desc())
        .limit(1)
        .with_for_update()
    )
    version = previous.version + 1 if previous else 1
    estimate = Estimate(
        organization_id=user.organization_id,
        request_id=request.id,
        version=version,
        previous_version_id=previous.id if previous else None,
        created_by=user.id,
    )
    session.add(estimate)
    await session.flush()
    await _replace_lines(session, estimate, data)
    session.add(_event(estimate, user, None, data.comment))
    session.add(
        AuditLog(
            organization_id=user.organization_id,
            actor_id=user.id,
            action="estimate.created",
            resource_type="estimate",
            resource_id=str(estimate.id),
            after={"request_id": str(request.id), "version": estimate.version},
        )
    )
    session.add(
        IdempotencyRecord(
            organization_id=user.organization_id,
            key=idempotency_key,
            payload_hash=payload_hash,
            resource_id=estimate.id,
        )
    )
    await session.commit()
    await session.refresh(estimate)
    return await _response(session, estimate)


@router.put("/estimates/{estimate_id}", response_model=EstimateOut)
async def update_draft(
    estimate_id: UUID,
    data: EstimateDraft,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> EstimateOut:
    if user.role not in MANAGER_ROLES:
        raise HTTPException(403, "Role cannot edit estimates")
    estimate = await session.scalar(
        select(Estimate)
        .where(
            Estimate.id == estimate_id,
            Estimate.organization_id == user.organization_id,
        )
        .with_for_update()
    )
    if estimate is None:
        raise HTTPException(404, "Estimate not found")
    if estimate.status != EstimateStatus.DRAFT:
        raise HTTPException(409, "Submitted estimate versions are immutable")
    await _replace_lines(session, estimate, data)
    session.add(_event(estimate, user, EstimateStatus.DRAFT, data.comment))
    await session.commit()
    await session.refresh(estimate)
    return await _response(session, estimate)


@router.post("/estimates/{estimate_id}/submit", response_model=EstimateOut)
async def submit_estimate(
    estimate_id: UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> EstimateOut:
    if user.role not in MANAGER_ROLES:
        raise HTTPException(403, "Role cannot submit estimates")
    estimate = await session.scalar(
        select(Estimate)
        .where(
            Estimate.id == estimate_id,
            Estimate.organization_id == user.organization_id,
        )
        .with_for_update()
    )
    if estimate is None:
        raise HTTPException(404, "Estimate not found")
    if estimate.status != EstimateStatus.DRAFT:
        raise HTTPException(409, "Only draft estimates can be submitted")
    previous_status = estimate.status
    estimate.status = EstimateStatus.AWAITING_APPROVAL
    session.add(_event(estimate, user, previous_status, estimate.comment))
    request = await session.scalar(
        select(ServiceRequest).where(
            ServiceRequest.id == estimate.request_id,
            ServiceRequest.organization_id == user.organization_id,
        )
    )
    if request is None:
        raise HTTPException(404, "Request not found")
    session.add(
        AuditLog(
            organization_id=user.organization_id,
            actor_id=user.id,
            action="estimate.submitted",
            resource_type="estimate",
            resource_id=str(estimate.id),
            before={"status": previous_status.value},
            after={"status": estimate.status.value},
        )
    )
    enqueue_notifications(
        session,
        organization_id=user.organization_id,
        user_ids=[request.customer_id],
        event_key=f"estimate.submitted:{estimate.id}",
        title="Estimate awaits your decision",
        body=f"Estimate version {estimate.version}",
        request_id=request.id,
    )
    previous = (
        await session.scalar(
            select(Estimate)
            .where(
                Estimate.id == estimate.previous_version_id,
                Estimate.organization_id == user.organization_id,
            )
            .with_for_update()
        )
        if estimate.previous_version_id
        else None
    )
    if previous and previous.status == EstimateStatus.AWAITING_APPROVAL:
        old_status = previous.status
        previous.status = EstimateStatus.SUPERSEDED
        session.add(_event(previous, user, old_status, "Superseded by a newer version"))
    await session.commit()
    await session.refresh(estimate)
    return await _response(session, estimate)


@router.post("/estimates/{estimate_id}/decision", response_model=EstimateOut)
async def decide_estimate(
    estimate_id: UUID,
    decision: EstimateDecision,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> EstimateOut:
    if user.role != Role.CUSTOMER:
        raise HTTPException(403, "Only the customer can decide an estimate")
    estimate = await session.scalar(
        select(Estimate)
        .join(ServiceRequest, ServiceRequest.id == Estimate.request_id)
        .where(
            Estimate.id == estimate_id,
            Estimate.organization_id == user.organization_id,
            ServiceRequest.organization_id == user.organization_id,
            ServiceRequest.customer_id == user.id,
        )
        .with_for_update()
    )
    if estimate is None:
        raise HTTPException(404, "Estimate not found")
    if estimate.status != EstimateStatus.AWAITING_APPROVAL:
        raise HTTPException(409, "Estimate is not awaiting approval")
    old_status = estimate.status
    estimate.status = EstimateStatus.APPROVED if decision.approved else EstimateStatus.REJECTED
    estimate.decided_at = datetime.now(UTC)
    session.add(_event(estimate, user, old_status, decision.comment))
    session.add(
        AuditLog(
            organization_id=user.organization_id,
            actor_id=user.id,
            action="estimate.decided",
            resource_type="estimate",
            resource_id=str(estimate.id),
            before={"status": old_status.value},
            after={"status": estimate.status.value, "comment": decision.comment},
        )
    )
    managers = (
        await session.scalars(
            select(User.id).where(
                User.organization_id == user.organization_id,
                User.active.is_(True),
                User.role.in_(MANAGER_ROLES),
            )
        )
    ).all()
    enqueue_notifications(
        session,
        organization_id=user.organization_id,
        user_ids=managers,
        event_key=f"estimate.decision:{estimate.id}",
        title="Customer decided on the estimate",
        body=estimate.status.value,
        request_id=estimate.request_id,
    )
    await session.commit()
    await session.refresh(estimate)
    return await _response(session, estimate)


@router.post("/estimates/{estimate_id}/revise", response_model=EstimateOut, status_code=201)
async def revise_estimate(
    estimate_id: UUID,
    idempotency_key: str = Header(min_length=8, max_length=128),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> EstimateOut:
    if user.role not in MANAGER_ROLES:
        raise HTTPException(403, "Role cannot create estimate revisions")
    source = await session.scalar(
        select(Estimate)
        .where(
            Estimate.id == estimate_id,
            Estimate.organization_id == user.organization_id,
        )
        .with_for_update()
    )
    if source is None:
        raise HTTPException(404, "Estimate not found")
    if source.status in {EstimateStatus.DRAFT, EstimateStatus.SUPERSEDED}:
        raise HTTPException(409, "Choose an active submitted version to revise")
    source_lines = (
        await session.scalars(select(EstimateLine).where(EstimateLine.estimate_id == source.id))
    ).all()
    payload_hash = hashlib.sha256(f"estimate.revise:{estimate_id}".encode()).hexdigest()
    existing = await session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.organization_id == user.organization_id,
            IdempotencyRecord.key == idempotency_key,
        )
    )
    if existing:
        if existing.payload_hash != payload_hash:
            raise HTTPException(409, "Idempotency key was used with a different payload")
        saved = await session.scalar(
            select(Estimate).where(
                Estimate.id == existing.resource_id,
                Estimate.organization_id == user.organization_id,
            )
        )
        if saved is None:
            raise HTTPException(409, "Estimate idempotency record has no matching version")
        return await _response(session, saved)
    revised = Estimate(
        organization_id=user.organization_id,
        request_id=source.request_id,
        version=source.version + 1,
        previous_version_id=source.id,
        created_by=user.id,
        comment=source.comment,
    )
    session.add(revised)
    await session.flush()
    session.add_all(
        [
            EstimateLine(
                organization_id=user.organization_id,
                estimate_id=revised.id,
                kind=line.kind,
                description=line.description,
                inventory_item_id=line.inventory_item_id,
                quantity=line.quantity,
                unit_price_tyiyn=line.unit_price_tyiyn,
            )
            for line in source_lines
        ]
    )
    revised.total_tyiyn = source.total_tyiyn
    session.add(_event(revised, user, None, revised.comment))
    session.add(
        AuditLog(
            organization_id=user.organization_id,
            actor_id=user.id,
            action="estimate.revised",
            resource_type="estimate",
            resource_id=str(revised.id),
            after={"source_version_id": str(source.id), "version": revised.version},
        )
    )
    session.add(
        IdempotencyRecord(
            organization_id=user.organization_id,
            key=idempotency_key,
            payload_hash=payload_hash,
            resource_id=revised.id,
        )
    )
    await session.commit()
    await session.refresh(revised)
    return await _response(session, revised)


@router.get("/requests/{request_id}/estimates", response_model=list[EstimateOut])
async def list_estimates(
    request_id: UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[EstimateOut]:
    request = await _request_for_user(request_id, user, session)
    estimates = (
        await session.scalars(
            select(Estimate)
            .where(
                Estimate.request_id == request.id,
                Estimate.organization_id == user.organization_id,
            )
            .order_by(Estimate.version)
        )
    ).all()
    if user.role == Role.CUSTOMER:
        estimates = [estimate for estimate in estimates if estimate.status != EstimateStatus.DRAFT]
    return [await _response(session, estimate) for estimate in estimates]


@router.get("/estimates/{estimate_id}/events", response_model=list[EstimateEventOut])
async def estimate_history(
    estimate_id: UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[EstimateEventOut]:
    estimate = await session.scalar(
        select(Estimate)
        .join(ServiceRequest, ServiceRequest.id == Estimate.request_id)
        .where(
            Estimate.id == estimate_id,
            Estimate.organization_id == user.organization_id,
            ServiceRequest.organization_id == user.organization_id,
            *([ServiceRequest.customer_id == user.id] if user.role == Role.CUSTOMER else []),
            *([Estimate.status != EstimateStatus.DRAFT] if user.role == Role.CUSTOMER else []),
        )
    )
    if estimate is None:
        raise HTTPException(404, "Estimate not found")
    events = (
        await session.scalars(
            select(EstimateEvent)
            .where(
                EstimateEvent.estimate_id == estimate.id,
                EstimateEvent.organization_id == user.organization_id,
            )
            .order_by(EstimateEvent.created_at)
        )
    ).all()
    return [EstimateEventOut.model_validate(event) for event in events]
