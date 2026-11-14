"""Repeatable, additive demo data loader. It never deletes or resets existing rows."""

import asyncio
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal
from app.domain import EstimateStatus, Role
from app.models.domain_entities import (
    Asset,
    Category,
    Estimate,
    EstimateLine,
    InventoryItem,
    Property,
    Skill,
    SkillCategory,
    Technician,
    TechnicianSkill,
    TechnicianWorkingHour,
)
from app.models.entities import Organization, ServiceRequest, User

DEMO_PASSWORD = "FixFlow-Demo-Only-2026!"
HASH = PasswordHash.recommended()


def stable_id(path: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"fixflow/demo/{path}")


async def get_or_add(session: AsyncSession, model: type, row_id: UUID, **values):
    existing = await session.get(model, row_id)
    if existing is not None:
        return existing, False
    created = model(id=row_id, **values)
    session.add(created)
    await session.flush()
    return created, True


async def add_if_missing(session: AsyncSession, model: type, **criteria):
    existing = await session.scalar(select(model).filter_by(**criteria))
    if existing is not None:
        return existing, False
    created = model(**criteria)
    session.add(created)
    await session.flush()
    return created, True


async def seed(session: AsyncSession) -> tuple[int, list[tuple[str, UUID]]]:
    if settings.app_env == "production":
        raise RuntimeError("Demo seed is disabled when APP_ENV=production")
    created_count = 0
    organizations: list[tuple[str, UUID]] = []
    for org_index, (slug, label) in enumerate(
        (("north", "Demo Service North"), ("south", "Demo Service South")), 1
    ):
        org, created = await get_or_add(
            session,
            Organization,
            stable_id(f"org/{slug}"),
            name=label,
            timezone="Asia/Bishkek",
        )
        created_count += int(created)
        organizations.append((org.name, org.id))
        roles: dict[Role, User] = {}
        for role in Role:
            user, created = await get_or_add(
                session,
                User,
                stable_id(f"user/{org_index}/{role.value.lower()}"),
                organization_id=org.id,
                email=f"{role.value.lower()}-{org_index}@demo.fixflow.local",
                name=f"Demo {role.value.replace('_', ' ').title()} {label.rsplit(' ', 1)[-1]}",
                role=role,
                password_hash=HASH.hash(DEMO_PASSWORD),
            )
            created_count += int(created)
            roles[role] = user

        prop, created = await get_or_add(
            session,
            Property,
            stable_id(f"property/{slug}/main"),
            organization_id=org.id,
            name=f"{label} — Central Building",
            code=f"{slug.upper()}-MAIN",
            address="Demo address, Bishkek",
        )
        created_count += int(created)
        category, created = await get_or_add(
            session,
            Category,
            stable_id(f"category/{slug}/plumbing"),
            organization_id=org.id,
            name="Plumbing",
        )
        created_count += int(created)
        skill, created = await get_or_add(
            session,
            Skill,
            stable_id(f"skill/{slug}/plumbing"),
            organization_id=org.id,
            name="Plumbing repair",
        )
        created_count += int(created)
        _, created = await add_if_missing(
            session,
            SkillCategory,
            organization_id=org.id,
            category_id=category.id,
            skill_id=skill.id,
        )
        created_count += int(created)

        technician, created = await get_or_add(
            session,
            Technician,
            stable_id(f"technician/{org.id}"),
            organization_id=org.id,
            user_id=roles[Role.TECHNICIAN].id,
        )
        created_count += int(created)
        _, created = await add_if_missing(
            session,
            TechnicianSkill,
            organization_id=org.id,
            technician_id=technician.id,
            skill_id=skill.id,
        )
        created_count += int(created)
        for weekday in range(5):
            _, created = await add_if_missing(
                session,
                TechnicianWorkingHour,
                organization_id=org.id,
                technician_id=technician.id,
                weekday=weekday,
                start_minute=9 * 60,
                end_minute=17 * 60,
            )
            created_count += int(created)

        assets: list[Asset] = []
        for number, asset_name in enumerate(("Main water heater", "Lobby circulation pump"), 1):
            asset, created = await get_or_add(
                session,
                Asset,
                stable_id(f"asset/{slug}/{number}"),
                organization_id=org.id,
                property_id=prop.id,
                category_id=category.id,
                asset_tag=f"{slug.upper()}-EQ-{number:02}",
                name=asset_name,
            )
            assets.append(asset)
            created_count += int(created)

        stock: list[InventoryItem] = []
        for sku, name, unit, amount in (
            ("PIPE-SEAL", "Pipe sealant", "tube", 20),
            ("VALVE-15", "15 mm shutoff valve", "piece", 12),
            ("FILTER-A", "Heating filter", "piece", 8),
        ):
            item, created = await get_or_add(
                session,
                InventoryItem,
                stable_id(f"inventory/{slug}/{sku.lower()}"),
                organization_id=org.id,
                sku=sku,
                name=name,
                unit=unit,
                quantity_on_hand=amount,
                minimum_quantity=2,
            )
            stock.append(item)
            created_count += int(created)

        requests: list[ServiceRequest] = []
        for index in range(25):
            request, created = await get_or_add(
                session,
                ServiceRequest,
                stable_id(f"request/{(org_index - 1) * 25 + index + 1}"),
                organization_id=org.id,
                customer_id=roles[Role.CUSTOMER].id,
                property_id=prop.id,
                asset_id=assets[index % len(assets)].id,
                category_id=category.id,
                title=f"Demo plumbing request {index + 1:02}",
                description="Seeded example request for evaluating the FixFlow service workflow.",
                priority="NORMAL",
            )
            requests.append(request)
            created_count += int(created)

        estimate, created = await get_or_add(
            session,
            Estimate,
            stable_id(f"estimate/{slug}/1"),
            organization_id=org.id,
            request_id=requests[0].id,
            version=1,
            status=EstimateStatus.DRAFT,
            total_tyiyn=17500,
            comment="Demo estimate ready for review",
            created_by=roles[Role.DISPATCHER].id,
        )
        created_count += int(created)
        if created:
            for index, (kind, description, item, quantity, price) in enumerate(
                (
                    ("LABOR", "Plumbing inspection and repair", None, "1", 10000),
                    ("MATERIAL", stock[0].name, stock[0], "1", 7500),
                ),
                1,
            ):
                session.add(
                    EstimateLine(
                        id=stable_id(f"estimate/{slug}/1/line/{index}"),
                        organization_id=org.id,
                        estimate_id=estimate.id,
                        kind=kind,
                        description=description,
                        inventory_item_id=item.id if item else None,
                        quantity=Decimal(quantity),
                        unit_price_tyiyn=price,
                    )
                )
                created_count += 1
        await session.flush()
    await session.commit()
    return created_count, organizations


async def main() -> None:
    async with SessionLocal() as session:
        created, organizations = await seed(session)
    print(f"Seed complete: added {created} rows; existing rows were retained.")
    print("Demo-only password: " + DEMO_PASSWORD)
    for name, organization_id in organizations:
        print(f"Organization ID for {name}: {organization_id}")


if __name__ == "__main__":
    asyncio.run(main())
