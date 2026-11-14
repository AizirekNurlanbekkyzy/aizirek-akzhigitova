import asyncio

from pwdlib import PasswordHash
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.entities import Organization, Role, ServiceRequest, User

HASH = PasswordHash.recommended()
DEMO_PASSWORD = "FixFlow-Demo-Only-2026!"


async def seed() -> None:
    async with SessionLocal() as session:
        if await session.scalar(select(Organization.id).limit(1)):
            print("Seed skipped: database already contains organizations.")
            return
        orgs = [Organization(name="Demo Service North"), Organization(name="Demo Service South")]
        session.add_all(orgs)
        await session.flush()
        for org_index, org in enumerate(orgs):
            for role in Role:
                session.add(
                    User(
                        organization_id=org.id,
                        email=f"{role.value.lower()}-{org_index + 1}@demo.fixflow.local",
                        name=f"Demo {role.value.title()}",
                        role=role,
                        password_hash=HASH.hash(DEMO_PASSWORD),
                    )
                )
        await session.flush()
        customers = (await session.scalars(select(User).where(User.role == Role.CUSTOMER))).all()
        for index in range(50):
            customer = customers[index % len(customers)]
            session.add(
                ServiceRequest(
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
