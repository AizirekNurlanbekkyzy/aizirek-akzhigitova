from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.entities import RequestStatus


class RequestCreate(BaseModel):
    title: str = Field(min_length=5, max_length=120)
    description: str = Field(min_length=20, max_length=3000)
    priority: str = Field(default="NORMAL", pattern="^(LOW|NORMAL|HIGH)$")


class RequestOut(BaseModel):
    id: UUID
    title: str
    description: str
    priority: str
    status: RequestStatus
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class StatusChange(BaseModel):
    status: RequestStatus
    reason: str | None = Field(default=None, max_length=1000)
