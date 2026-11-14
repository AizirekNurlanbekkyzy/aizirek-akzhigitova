import hashlib
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.core.db import get_session
from app.domain import AssignmentStatus, Role
from app.models.domain_entities import Assignment, AuditLog, Note, Technician
from app.models.entities import IdempotencyRecord, ServiceRequest, User
from app.schemas.notes import NoteCreate, NoteOut

router = APIRouter(prefix="/requests/{request_id}/notes", tags=["notes"])


async def _visible_request(request_id: UUID, user: User, session: AsyncSession) -> ServiceRequest:
    conditions = [
        ServiceRequest.id == request_id,
        ServiceRequest.organization_id == user.organization_id,
    ]
    if user.role == Role.CUSTOMER:
        conditions.append(ServiceRequest.customer_id == user.id)
    request = await session.scalar(select(ServiceRequest).where(*conditions))
    if request is None:
        raise HTTPException(404, "Request not found")
    if user.role == Role.TECHNICIAN:
        assignment = await session.scalar(
            select(Assignment.id)
            .join(Technician, Technician.id == Assignment.technician_id)
            .where(
                Assignment.organization_id == user.organization_id,
                Assignment.request_id == request.id,
                Assignment.status.in_({AssignmentStatus.ACCEPTED, AssignmentStatus.COMPLETED}),
                Technician.organization_id == user.organization_id,
                Technician.user_id == user.id,
                Technician.active.is_(True),
            )
            .limit(1)
        )
        if assignment is None:
            raise HTTPException(404, "Request not found")
    return request


@router.get("", response_model=list[NoteOut])
async def list_notes(
    request_id: UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Note]:
    await _visible_request(request_id, user, session)
    query = select(Note).where(
        Note.organization_id == user.organization_id,
        Note.request_id == request_id,
    )
    if user.role == Role.CUSTOMER:
        query = query.where(Note.internal_only.is_(False))
    return list((await session.scalars(query.order_by(Note.created_at))).all())


@router.post("", response_model=NoteOut, status_code=201)
async def create_note(
    request_id: UUID,
    data: NoteCreate,
    idempotency_key: str = Header(min_length=8, max_length=128),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Note:
    request = await _visible_request(request_id, user, session)
    if user.role == Role.CUSTOMER and data.internal_only:
        raise HTTPException(403, "Customers cannot create internal notes")
    payload_hash = hashlib.sha256(
        f"request.note:{request_id}:{data.model_dump_json()}".encode()
    ).hexdigest()
    existing = await session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.organization_id == user.organization_id,
            IdempotencyRecord.key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.payload_hash != payload_hash:
            raise HTTPException(409, "Idempotency key was used with a different payload")
        note = await session.scalar(
            select(Note).where(
                Note.id == existing.resource_id,
                Note.organization_id == user.organization_id,
                Note.request_id == request.id,
            )
        )
        if note is None:
            raise HTTPException(409, "Idempotency record has no matching note")
        return note
    note = Note(
        organization_id=user.organization_id,
        request_id=request.id,
        author_id=user.id,
        body=data.body,
        internal_only=data.internal_only,
    )
    session.add(note)
    await session.flush()
    session.add(
        AuditLog(
            organization_id=user.organization_id,
            actor_id=user.id,
            action="request.note_created",
            resource_type="note",
            resource_id=str(note.id),
            after={"request_id": str(request.id), "internal_only": note.internal_only},
        )
    )
    session.add(
        IdempotencyRecord(
            organization_id=user.organization_id,
            key=idempotency_key,
            payload_hash=payload_hash,
            resource_id=note.id,
        )
    )
    try:
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
        if existing.payload_hash != payload_hash:
            raise HTTPException(409, "Idempotency key was used with a different payload") from None
        note = await session.scalar(
            select(Note).where(
                Note.id == existing.resource_id,
                Note.organization_id == user.organization_id,
                Note.request_id == request.id,
            )
        )
        if note is None:
            raise HTTPException(409, "Idempotency record has no matching note") from None
        return note
    await session.refresh(note)
    return note
