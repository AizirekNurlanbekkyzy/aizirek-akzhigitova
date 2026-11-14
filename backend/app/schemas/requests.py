from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.entities import RequestStatus


class RequestCreate(BaseModel):
    title: str = Field(min_length=5, max_length=120)
    description: str = Field(min_length=20, max_length=3000)
    priority: str = Field(default="NORMAL", pattern="^(LOW|NORMAL|HIGH)$")
    property_id: UUID | None = None
    asset_id: UUID | None = None
    category_id: UUID | None = None
    desired_visit_at: datetime | None = None

    @field_validator("desired_visit_at")
    @classmethod
    def visit_time_must_include_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            if value.tzinfo is None:
                raise ValueError("desired_visit_at must include a timezone")
            return value.astimezone(UTC)
        return value


class RequestOut(BaseModel):
    id: UUID
    title: str
    description: str
    priority: str
    status: RequestStatus
    created_at: datetime
    property_id: UUID | None = None
    asset_id: UUID | None = None
    category_id: UUID | None = None
    desired_visit_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class StatusChange(BaseModel):
    status: RequestStatus
    reason: str | None = Field(default=None, max_length=1000)
