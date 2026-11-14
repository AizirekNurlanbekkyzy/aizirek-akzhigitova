import asyncio
from uuid import NAMESPACE_URL, uuid5

from pwdlib import PasswordHash
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.domain_entities import Technician, TechnicianWorkingHour
from app.models.entities import Organization, Role, ServiceRequest, User

HASH = PasswordHash.recommended()
DEMO_PASSWORD = "FixFlow-Demo-Only-2026!"


async def seed() -> None:
    async with SessionLocal() as session:
        if await session.scalar(select(Organization.id).limit(1)):
            print("Seed skipped: database already contains organizations.")
            return
        orgs = [
            Organization(
                id=uuid5(NAMESPACE_URL, "fixflow/demo/org/north"), name="Demo Service North"
            ),
            Organization(
                id=uuid5(NAMESPACE_URL, "fixflow/demo/org/south"), name="Demo Service South"
            ),
        ]
        session.add_all(orgs)
        await session.flush()
        for org_index, org in enumerate(orgs):
            for role in Role:
                session.add(
                    User(
                        id=uuid5(
                            NAMESPACE_URL,
                            f"fixflow/demo/user/{org_index + 1}/{role.value.lower()}",
                        ),
                        organization_id=org.id,
                        email=f"{role.value.lower()}-{org_index + 1}@demo.fixflow.local",
                        name=f"Demo {role.value.title()}",
                        role=role,
                        password_hash=HASH.hash(DEMO_PASSWORD),
                    )
                )
        await session.flush()
        technicians = (
            await session.scalars(select(User).where(User.role == Role.TECHNICIAN))
        ).all()
        for technician_user in technicians:
            technician = Technician(
                id=uuid5(
                    NAMESPACE_URL, f"fixflow/demo/technician/{technician_user.organization_id}"
                ),
                organization_id=technician_user.organization_id,
                user_id=technician_user.id,
            )
            session.add(technician)
            await session.flush()
            session.add_all(
                [
                    TechnicianWorkingHour(
                        organization_id=technician_user.organization_id,
                        technician_id=technician.id,
                        weekday=weekday,
                        start_minute=9 * 60,
                        end_minute=17 * 60,
                    )
                    for weekday in range(5)
                ]
            )
        customers = (await session.scalars(select(User).where(User.role == Role.CUSTOMER))).all()
        for index in range(50):
            customer = customers[index % len(customers)]
            session.add(
                ServiceRequest(
                    id=uuid5(NAMESPACE_URL, f"fixflow/demo/request/{index + 1}"),
                    organization_id=customer.organization_id,
                    customer_id=customer.id,
                    title=f"Demo maintenance request {index + 1:02}",
                    description="Seeded example request for evaluating FixFlow workflows.",
                )
            )
        await session.commit()
    print("Seeded two demo organizations and 50 requests. Demo-only password: " + DEMO_PASSWORD)
    for org in orgs:
        print(f"Organization ID for {org.name}: {org.id}")


if __name__ == "__main__":
    asyncio.run(seed())
