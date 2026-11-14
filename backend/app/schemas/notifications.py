from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    id: UUID
    request_id: UUID | None
    event_key: str
    title: str
    body: str
    read_at: datetime | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
