from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
    internal_only: bool = False


class NoteOut(BaseModel):
    id: UUID
    request_id: UUID
    author_id: UUID
    body: str
    internal_only: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
