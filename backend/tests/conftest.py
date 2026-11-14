from collections.abc import AsyncIterator
from uuid import UUID

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import get_session
from app.domain import Role
from app.main import app
from app.models import Base, Organization, User
from app.models.domain_entities import Technician, TechnicianWorkingHour


@pytest_asyncio.fixture
async def api_client() -> AsyncIterator[tuple[AsyncClient, UUID, UUID, UUID]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def test_session() -> AsyncIterator[AsyncSession]:
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = test_session
    async with sessions() as session:
        first = Organization(name="Test Tenant A")
        second = Organization(name="Test Tenant B")
        session.add_all([first, second])
        await session.flush()
        password_hash = PasswordHash.recommended().hash("integration-test-password")
        customer_a = User(
            organization_id=first.id,
            email="customer-a@tenant-a.example.com",
            password_hash=password_hash,
            name="Tenant A Customer",
            role=Role.CUSTOMER,
        )
        customer_b = User(
            organization_id=second.id,
            email="customer-b@tenant-b.example.com",
            password_hash=password_hash,
            name="Tenant B Customer",
            role=Role.CUSTOMER,
        )
        dispatcher_a = User(
            organization_id=first.id,
            email="dispatcher-a@tenant-a.example.com",
            password_hash=password_hash,
            name="Tenant A Dispatcher",
            role=Role.DISPATCHER,
        )
        admin_a = User(
            organization_id=first.id,
            email="admin-a@tenant-a.example.com",
            password_hash=password_hash,
            name="Tenant A Admin",
            role=Role.ORGANIZATION_ADMIN,
        )
        technician_a = User(
            organization_id=first.id,
            email="technician-a@tenant-a.example.com",
            password_hash=password_hash,
            name="Tenant A Technician",
            role=Role.TECHNICIAN,
        )
        session.add_all([customer_a, customer_b, dispatcher_a, admin_a, technician_a])
        await session.flush()
        technician = Technician(organization_id=first.id, user_id=technician_a.id)
        session.add(technician)
        await session.flush()
        session.add_all(
            [
                TechnicianWorkingHour(
                    organization_id=first.id,
                    technician_id=technician.id,
                    weekday=weekday,
                    start_minute=0,
                    end_minute=1440,
                )
                for weekday in range(7)
            ]
        )
        await session.commit()
        org_a, org_b = first.id, second.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, org_a, org_b, customer_a.id
    app.dependency_overrides.clear()
    await engine.dispose()


async def login(client: AsyncClient, email: str, organization_id: UUID) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "integration-test-password",
            "organization_id": str(organization_id),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]
