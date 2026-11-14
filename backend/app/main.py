from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import assignments, audit, auth, estimates, inventory, notes, notifications, requests
from app.core.config import settings
from app.core.db import engine, get_session


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Schema changes in deployed environments are applied by Alembic.
    yield
    await engine.dispose()


app = FastAPI(
    title="FixFlow API",
    version="0.1.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(requests.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(estimates.router, prefix="/api/v1")
app.include_router(assignments.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(notes.router, prefix="/api/v1")


@app.get("/health/live", tags=["health"])
async def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def ready(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ready"}
