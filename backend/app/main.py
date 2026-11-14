from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, requests
from app.core.db import engine


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
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(requests.router, prefix="/api/v1")


@app.get("/health/live", tags=["health"])
async def live() -> dict[str, str]:
    return {"status": "ok"}
