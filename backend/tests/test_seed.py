import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings, settings
from app.models import Base, Organization, ServiceRequest, User
from app.models.domain_entities import Asset, Estimate, InventoryItem, Technician
from app.seed import seed


def test_settings_reject_placeholder_and_low_entropy_jwt_secrets() -> None:
    with pytest.raises(ValueError, match="generated secret"):
        Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            jwt_secret="GENERATE_SECRET_DO_NOT_USE_0123456789abcdef",
            app_env="test",
        )
    with pytest.raises(ValueError, match="sufficient randomness"):
        Settings(database_url="sqlite+aiosqlite:///:memory:", jwt_secret="x" * 48, app_env="test")
    with pytest.raises(ValueError, match="cannot be used in production"):
        Settings(
            database_url="sqlite+aiosqlite:///:memory:",
            jwt_secret="test-secret-for-fixflow-tests-only-000000000000000000",
            app_env="production",
        )


async def test_seed_is_repeatable_additive_and_includes_demo_workflows() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        first_count, organizations = await seed(session)
        second_count, organizations_again = await seed(session)
        assert first_count > 0
        assert second_count == 0
        assert organizations == organizations_again

        for model, expected in (
            (Organization, 2),
            (User, 8),
            (ServiceRequest, 50),
            (Technician, 2),
            (Asset, 4),
            (Estimate, 2),
            (InventoryItem, 6),
        ):
            count = await session.scalar(select(func.count()).select_from(model))
            assert count == expected, model.__name__
    await engine.dispose()


async def test_demo_seed_refuses_production(monkeypatch) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(settings, "app_env", "production")
    async with sessions() as session:
        with pytest.raises(RuntimeError, match="disabled"):
            await seed(session)
    await engine.dispose()
