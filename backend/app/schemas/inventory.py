from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InventoryItemCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=2, max_length=160)
    unit: str = Field(min_length=1, max_length=24)
    minimum_quantity: int = Field(default=0, ge=0)


class InventoryItemOut(BaseModel):
    id: UUID
    sku: str
    name: str
    unit: str
    quantity_on_hand: int
    minimum_quantity: int
    model_config = ConfigDict(from_attributes=True)


class StockMovementCreate(BaseModel):
    quantity_delta: int
    reason: str = Field(min_length=3, max_length=300)

    @field_validator("quantity_delta")
    @classmethod
    def quantity_delta_must_not_be_zero(cls, value: int) -> int:
        if value == 0:
            raise ValueError("quantity_delta must not be zero")
        return value


class StockMovementOut(BaseModel):
    id: UUID
    item_id: UUID
    quantity_delta: int
    resulting_quantity: int
    reason: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
