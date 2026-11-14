from __future__ import annotations

import hashlib
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.core.db import get_session
from app.domain import Role
from app.models.domain_entities import InventoryItem, StockMovement
from app.models.entities import User
from app.schemas.inventory import (
    InventoryItemCreate,
    InventoryItemOut,
    StockMovementCreate,
    StockMovementOut,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])
MANAGEMENT_ROLES = {Role.DISPATCHER, Role.ORGANIZATION_ADMIN}


def require_inventory_manager(user: User) -> None:
    if user.role not in MANAGEMENT_ROLES:
        raise HTTPException(403, "Role cannot access inventory management")


@router.post("/items", response_model=InventoryItemOut, status_code=201)
async def create_item(
    data: InventoryItemCreate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> InventoryItem:
    if user.role != Role.ORGANIZATION_ADMIN:
        raise HTTPException(403, "Only organization administrators can add inventory items")
    item = InventoryItem(organization_id=user.organization_id, **data.model_dump())
    session.add(item)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "SKU already exists in this organization") from None
    await session.refresh(item)
    return item


@router.get("/items", response_model=list[InventoryItemOut])
async def list_items(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[InventoryItem]:
    require_inventory_manager(user)
    return list(
        (
            await session.scalars(
                select(InventoryItem)
                .where(InventoryItem.organization_id == user.organization_id)
                .order_by(InventoryItem.name)
            )
        ).all()
    )


@router.post("/items/{item_id}/movements", response_model=StockMovementOut, status_code=201)
async def record_movement(
    item_id: UUID,
    data: StockMovementCreate,
    idempotency_key: str = Header(min_length=8, max_length=128),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> StockMovement:
    require_inventory_manager(user)
    item = await session.scalar(
        select(InventoryItem)
        .where(
            InventoryItem.id == item_id,
            InventoryItem.organization_id == user.organization_id,
            InventoryItem.active.is_(True),
        )
        .with_for_update()
    )
    if item is None:
        raise HTTPException(404, "Inventory item not found")

    payload_hash = hashlib.sha256(f"{item_id}:{data.model_dump_json()}".encode()).hexdigest()
    existing = await session.scalar(
        select(StockMovement).where(
            StockMovement.organization_id == user.organization_id,
            StockMovement.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        if existing.payload_hash != payload_hash:
            raise HTTPException(409, "Idempotency key was used with a different movement")
        return existing

    next_quantity = item.quantity_on_hand + data.quantity_delta
    if next_quantity < 0:
        raise HTTPException(409, "Insufficient stock; inventory cannot become negative")

    movement = StockMovement(
        organization_id=user.organization_id,
        item_id=item.id,
        actor_id=user.id,
        quantity_delta=data.quantity_delta,
        resulting_quantity=next_quantity,
        reason=data.reason,
        idempotency_key=idempotency_key,
        payload_hash=payload_hash,
    )
    item.quantity_on_hand = next_quantity
    session.add(movement)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await session.scalar(
            select(StockMovement).where(
                StockMovement.organization_id == user.organization_id,
                StockMovement.idempotency_key == idempotency_key,
            )
        )
        if existing is None:
            raise
        if existing.payload_hash != payload_hash:
            raise HTTPException(409, "Idempotency key was used with a different movement") from None
        return existing
    await session.refresh(movement)
    return movement
