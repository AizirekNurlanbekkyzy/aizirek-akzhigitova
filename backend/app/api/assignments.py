from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.core.db import get_session
from app.domain import AssignmentStatus, RequestStatus, Role
from app.models.domain_entities import (
    Assignment,
    AssignmentEvent,
    AuditLog,
    SkillCategory,
    Technician,
    TechnicianSkill,
    TechnicianWorkingHour,
)
from app.models.entities import Organization, RequestEvent, ServiceRequest, User
from app.schemas.assignments import (
    AssignmentBoardOut,
    AssignmentCreate,
    AssignmentDecline,
    AssignmentOut,
    TechnicianProfileOut,
)
from app.services.notifications import enqueue_notifications

router = APIRouter(tags=["assignments"])
DISPATCH_ROLES = {Role.DISPATCHER, Role.ORGANIZATION_ADMIN}
BUSY_ASSIGNMENT_STATES = {AssignmentStatus.OFFERED, AssignmentStatus.ACCEPTED}


@router.get("/technicians")
async def list_technicians(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
) -> list[dict[str, str | bool]]:
    if user.role not in DISPATCH_ROLES:
        raise HTTPException(403, "Role cannot list technicians")
    rows = (
        await session.execute(
            select(Technician, User)
            .join(User, User.id == Technician.user_id)
            .where(
                Technician.organization_id == user.organization_id,
                Technician.active.is_(True),
                User.organization_id == user.organization_id,
                User.active.is_(True),
            )
            .order_by(User.name)
        )
    ).all()
    return [
        {"id": str(tech.id), "user_id": str(person.id), "name": person.name, "active": tech.active}
        for tech, person in rows
    ]


@router.get("/assignments", response_model=list[AssignmentBoardOut])
async def assignment_board(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
) -> list[AssignmentBoardOut]:
    if user.role not in DISPATCH_ROLES:
        raise HTTPException(403, "Role cannot view the dispatch schedule")
    rows = (
        await session.execute(
            select(Assignment, ServiceRequest.title, User.name)
            .join(ServiceRequest, ServiceRequest.id == Assignment.request_id)
            .join(Technician, Technician.id == Assignment.technician_id)
            .join(User, User.id == Technician.user_id)
            .where(
                Assignment.organization_id == user.organization_id,
                ServiceRequest.organization_id == user.organization_id,
                Technician.organization_id == user.organization_id,
            )
            .order_by(Assignment.starts_at.desc())
        )
    ).all()
    return [
        AssignmentBoardOut(
            id=assignment.id,
            request_id=assignment.request_id,
            technician_id=assignment.technician_id,
            starts_at=assignment.starts_at,
            ends_at=assignment.ends_at,
            status=assignment.status,
            created_at=assignment.created_at,
            request_title=title,
            technician_name=name,
        )
        for assignment, title, name in rows
    ]


@router.get("/technicians/me", response_model=TechnicianProfileOut)
async def technician_profile(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> TechnicianProfileOut:
    if user.role != Role.TECHNICIAN:
        raise HTTPException(403, "Technician role required")
    profile = await session.scalar(
        select(Technician).where(
            Technician.organization_id == user.organization_id,
            Technician.user_id == user.id,
            Technician.active.is_(True),
        )
    )
    if profile is None:
        raise HTTPException(404, "Technician profile not found")
    return TechnicianProfileOut(
        id=profile.id,
        user_id=user.id,
        name=user.name,
        active=profile.active,
    )


@router.get("/technician/assignments", response_model=list[AssignmentOut])
async def technician_assignments(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Assignment]:
    if user.role != Role.TECHNICIAN:
        raise HTTPException(403, "Technician role required")
    technician = await session.scalar(
        select(Technician).where(
            Technician.organization_id == user.organization_id,
            Technician.user_id == user.id,
            Technician.active.is_(True),
        )
    )
    if technician is None:
        raise HTTPException(404, "Technician profile not found")
    return list(
        (
            await session.scalars(
                select(Assignment)
                .where(
                    Assignment.organization_id == user.organization_id,
                    Assignment.technician_id == technician.id,
                    Assignment.status.in_(BUSY_ASSIGNMENT_STATES),
                )
                .order_by(Assignment.starts_at)
            )
        ).all()
    )


def _record_event(
    assignment: Assignment,
    actor: User,
    old_status: AssignmentStatus | None,
    reason: str | None = None,
) -> AssignmentEvent:
    return AssignmentEvent(
        organization_id=actor.organization_id,
        assignment_id=assignment.id,
        actor_id=actor.id,
        from_status=old_status.value if old_status else None,
        to_status=assignment.status.value,
        reason=reason,
    )


@router.post("/requests/{request_id}/assignments", response_model=AssignmentOut, status_code=201)
async def create_assignment(
    request_id: UUID,
    data: AssignmentCreate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Assignment:
    if user.role not in DISPATCH_ROLES:
        raise HTTPException(403, "Role cannot assign technicians")
    request = await session.scalar(
        select(ServiceRequest)
        .where(
            ServiceRequest.id == request_id,
            ServiceRequest.organization_id == user.organization_id,
        )
        .with_for_update()
    )
    if request is None:
        raise HTTPException(404, "Request not found")
    if request.status != RequestStatus.TRIAGED:
        raise HTTPException(409, "Only triaged requests can be scheduled")
    if data.ends_at <= data.starts_at:
        raise HTTPException(422, "Assignment end time must be after its start time")
    if data.starts_at <= datetime.now(UTC):
        raise HTTPException(422, "Assignment must be scheduled in the future")

    technician = await session.scalar(
        select(Technician)
        .where(
            Technician.id == data.technician_id,
            Technician.organization_id == user.organization_id,
            Technician.active.is_(True),
        )
        .with_for_update()
    )
    if technician is None:
        raise HTTPException(404, "Technician not found")
    technician_user = await session.scalar(
        select(User).where(
            User.id == technician.user_id,
            User.organization_id == user.organization_id,
            User.role == Role.TECHNICIAN,
            User.active.is_(True),
        )
    )
    if technician_user is None:
        raise HTTPException(409, "Technician account is disabled")

    organization = await session.get(Organization, user.organization_id)
    if organization is None or not organization.active:
        raise HTTPException(404, "Organization not found")
    local_start = data.starts_at.astimezone(ZoneInfo(organization.timezone))
    local_end = data.ends_at.astimezone(ZoneInfo(organization.timezone))
    if local_start.date() != local_end.date():
        raise HTTPException(422, "Assignment must fit within one local workday")
    start_minute = local_start.hour * 60 + local_start.minute
    end_minute = local_end.hour * 60 + local_end.minute
    workday = await session.scalar(
        select(TechnicianWorkingHour).where(
            TechnicianWorkingHour.organization_id == user.organization_id,
            TechnicianWorkingHour.technician_id == technician.id,
            TechnicianWorkingHour.weekday == local_start.weekday(),
        )
    )
    if workday is None or start_minute < workday.start_minute or end_minute > workday.end_minute:
        raise HTTPException(409, "Assignment falls outside technician working hours")

    if request.category_id:
        required = set(
            (
                await session.scalars(
                    select(SkillCategory.skill_id).where(
                        SkillCategory.organization_id == user.organization_id,
                        SkillCategory.category_id == request.category_id,
                    )
                )
            ).all()
        )
        available = set(
            (
                await session.scalars(
                    select(TechnicianSkill.skill_id).where(
                        TechnicianSkill.organization_id == user.organization_id,
                        TechnicianSkill.technician_id == technician.id,
                    )
                )
            ).all()
        )
        if not required.issubset(available):
            raise HTTPException(409, "Technician does not have the required skills")

    overlap = await session.scalar(
        select(Assignment.id)
        .where(
            Assignment.organization_id == user.organization_id,
            Assignment.technician_id == technician.id,
            Assignment.status.in_(BUSY_ASSIGNMENT_STATES),
            Assignment.starts_at < data.ends_at,
            Assignment.ends_at > data.starts_at,
        )
        .limit(1)
    )
    if overlap:
        raise HTTPException(409, "Technician already has an overlapping assignment")

    assignment = Assignment(
        organization_id=user.organization_id,
        request_id=request.id,
        technician_id=technician.id,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
    )
    old_request_status = request.status
    request.status = RequestStatus.SCHEDULED
    session.add(assignment)
    await session.flush()
    session.add(_record_event(assignment, user, None))
    session.add(
        AuditLog(
            organization_id=user.organization_id,
            actor_id=user.id,
            action="assignment.created",
            resource_type="assignment",
            resource_id=str(assignment.id),
            after={"request_id": str(request.id), "technician_id": str(technician.id)},
        )
    )
    enqueue_notifications(
        session,
        organization_id=user.organization_id,
        user_ids=[technician_user.id],
        event_key=f"assignment.offered:{assignment.id}",
        title="New technician assignment",
        body=request.title,
        request_id=request.id,
    )
    session.add(
        RequestEvent(
            organization_id=user.organization_id,
            request_id=request.id,
            actor_id=user.id,
            from_status=old_request_status.value,
            to_status=request.status.value,
        )
    )
    await session.commit()
    await session.refresh(assignment)
    return assignment


async def _get_assignment_for_technician(
    assignment_id: UUID,
    user: User,
    session: AsyncSession,
) -> tuple[Assignment, ServiceRequest]:
    if user.role != Role.TECHNICIAN:
        raise HTTPException(403, "Only assigned technicians can respond to assignments")
    assignment_ref = await session.scalar(
        select(Assignment).where(
            Assignment.id == assignment_id,
            Assignment.organization_id == user.organization_id,
        )
    )
    if assignment_ref is None:
        raise HTTPException(404, "Assignment not found")
    technician = await session.scalar(
        select(Technician).where(
            Technician.user_id == user.id,
            Technician.organization_id == user.organization_id,
            Technician.active.is_(True),
        )
    )
    if technician is None or technician.id != assignment_ref.technician_id:
        raise HTTPException(404, "Assignment not found")
    request = await session.scalar(
        select(ServiceRequest)
        .where(
            ServiceRequest.id == assignment_ref.request_id,
            ServiceRequest.organization_id == user.organization_id,
        )
        .with_for_update()
    )
    assignment = await session.scalar(
        select(Assignment)
        .where(
            Assignment.id == assignment_id,
            Assignment.organization_id == user.organization_id,
        )
        .with_for_update()
    )
    if request is None or assignment is None:
        raise HTTPException(404, "Assignment not found")
    return assignment, request


@router.post("/assignments/{assignment_id}/accept", response_model=AssignmentOut)
async def accept_assignment(
    assignment_id: UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Assignment:
    assignment, request = await _get_assignment_for_technician(assignment_id, user, session)
    if assignment.status != AssignmentStatus.OFFERED:
        raise HTTPException(409, "Assignment is no longer awaiting a response")
    if request.status != RequestStatus.SCHEDULED:
        raise HTTPException(409, "Request is no longer scheduled")
    assignment.status = AssignmentStatus.ACCEPTED
    old_request_status = request.status
    request.status = RequestStatus.ACCEPTED
    session.add(_record_event(assignment, user, AssignmentStatus.OFFERED))
    session.add(
        AuditLog(
            organization_id=user.organization_id,
            actor_id=user.id,
            action="assignment.accepted",
            resource_type="assignment",
            resource_id=str(assignment.id),
            before={"status": AssignmentStatus.OFFERED.value},
            after={"status": AssignmentStatus.ACCEPTED.value},
        )
    )
    session.add(
        RequestEvent(
            organization_id=user.organization_id,
            request_id=request.id,
            actor_id=user.id,
            from_status=old_request_status.value,
            to_status=request.status.value,
        )
    )
    await session.commit()
    await session.refresh(assignment)
    return assignment


@router.post("/assignments/{assignment_id}/decline", response_model=AssignmentOut)
async def decline_assignment(
    assignment_id: UUID,
    data: AssignmentDecline,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> Assignment:
    assignment, request = await _get_assignment_for_technician(assignment_id, user, session)
    if assignment.status != AssignmentStatus.OFFERED:
        raise HTTPException(409, "Assignment is no longer awaiting a response")
    assignment.status = AssignmentStatus.DECLINED
    old_request_status = request.status
    request.status = RequestStatus.TRIAGED
    session.add(_record_event(assignment, user, AssignmentStatus.OFFERED, data.reason))
    session.add(
        AuditLog(
            organization_id=user.organization_id,
            actor_id=user.id,
            action="assignment.declined",
            resource_type="assignment",
            resource_id=str(assignment.id),
            before={"status": AssignmentStatus.OFFERED.value},
            after={"status": AssignmentStatus.DECLINED.value, "reason": data.reason},
        )
    )
    session.add(
        RequestEvent(
            organization_id=user.organization_id,
            request_id=request.id,
            actor_id=user.id,
            from_status=old_request_status.value,
            to_status=request.status.value,
            reason=data.reason,
        )
    )
    await session.commit()
    await session.refresh(assignment)
    return assignment
