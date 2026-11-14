from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain import EstimateStatus


class EstimateLineInput(BaseModel):
    kind: Literal["LABOR", "MATERIAL"]
    description: str = Field(min_length=2, max_length=500)
    inventory_item_id: UUID | None = None
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    unit_price_tyiyn: int = Field(ge=0)


class EstimateDraft(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)
    lines: list[EstimateLineInput] = Field(min_length=1, max_length=50)


class EstimateDecision(BaseModel):
    approved: bool
    comment: str | None = Field(default=None, max_length=2000)


class EstimateLineOut(BaseModel):
    id: UUID
    kind: str
    description: str
    inventory_item_id: UUID | None
    quantity: Decimal
    unit_price_tyiyn: int
    model_config = ConfigDict(from_attributes=True)


class EstimateOut(BaseModel):
    id: UUID
    request_id: UUID
    version: int
    previous_version_id: UUID | None
    status: EstimateStatus
    total_tyiyn: int
    comment: str | None
    created_at: datetime
    decided_at: datetime | None
    lines: list[EstimateLineOut]


class EstimateEventOut(BaseModel):
    from_status: str | None
    to_status: str
    comment: str | None
    created_at: datetime
