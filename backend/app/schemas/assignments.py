from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.domain import AssignmentStatus


class AssignmentCreate(BaseModel):
    technician_id: UUID
    starts_at: datetime
    ends_at: datetime

    @field_validator("starts_at", "ends_at")
    @classmethod
    def scheduled_time_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Assignment time must include a timezone")
        return value.astimezone(UTC)


class AssignmentDecline(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class AssignmentOut(BaseModel):
    id: UUID
    request_id: UUID
    technician_id: UUID
    starts_at: datetime
    ends_at: datetime
    status: AssignmentStatus
    created_at: datetime


class AssignmentBoardOut(AssignmentOut):
    request_title: str
    technician_name: str


class TechnicianProfileOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    active: bool
