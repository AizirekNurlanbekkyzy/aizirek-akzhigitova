import re
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from pydantic import BaseModel, EmailStr, Field, TypeAdapter, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.domain import Role
from app.models.domain_entities import AuditLog
from app.models.entities import Organization, User

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
password_hash = PasswordHash.recommended()


def normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if normalized.endswith("@demo.fixflow.local"):
        if not re.fullmatch(r"[^@\s]+@demo\.fixflow\.local", normalized):
            raise ValueError("Invalid demo email address")
        return normalized
    return str(TypeAdapter(EmailStr).validate_python(normalized))


class Login(BaseModel):
    email: str
    password: str
    organization_id: UUID | None = None

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str) -> str:
        return normalize_email(value)


class Registration(BaseModel):
    email: str
    name: str | None = Field(default=None, min_length=2, max_length=160)
    password: str = Field(min_length=12, max_length=128)
    organization_id: UUID | None = None

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str) -> str:
        return normalize_email(value)


@router.post("/register", status_code=201)
async def register(
    data: Registration, session: AsyncSession = Depends(get_session)
) -> dict[str, str]:
    organization_id = data.organization_id or settings.default_organization_id
    if organization_id is None:
        raise HTTPException(
            status_code=503,
            detail="Customer registration is not configured for this service",
        )
    organization = await session.scalar(
        select(Organization).where(
            Organization.id == organization_id, Organization.active.is_(True)
        )
    )
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    if data.organization_id is None:
        existing_email = await session.scalar(
            select(User.id).where(User.email == data.email).limit(1)
        )
        if existing_email is not None:
            raise HTTPException(status_code=409, detail="Email is already registered")
    display_name = data.name.strip() if data.name and data.name.strip() else (
        data.email.split("@", 1)[0]
        .replace(".", " ")
        .replace("_", " ")
        .replace("-", " ")
        .title()
    )
    user = User(
        organization_id=organization.id,
        email=data.email,
        password_hash=password_hash.hash(data.password),
        name=display_name,
        role=Role.CUSTOMER,
    )
    session.add(user)
    try:
        await session.flush()
        session.add(
            AuditLog(
                organization_id=organization.id,
                actor_id=user.id,
                action="user.registered",
                resource_type="user",
                resource_id=str(user.id),
                after={"role": "CUSTOMER"},
            )
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Email is already registered") from exc
    return {"id": str(user.id), "email": user.email, "role": user.role.value}


@router.post("/login")
async def login(data: Login, session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    query = (
        select(User)
        .join(Organization, Organization.id == User.organization_id)
        .where(
            User.email == str(data.email).lower(),
            Organization.active.is_(True),
        )
    )
    if data.organization_id is not None:
        query = query.where(User.organization_id == data.organization_id)
    result = await session.scalars(query)
    matches = [
        user
        for user in result.all()
        if user.active and password_hash.verify(data.password, user.password_hash)
    ]
    if len(matches) != 1:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    user = matches[0]
    token = jwt.encode(
        {
            "sub": str(user.id),
            "org": str(user.organization_id),
            "role": user.role.value,
            "exp": datetime.now(UTC) + timedelta(minutes=settings.jwt_exp_minutes),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    return {"access_token": token, "token_type": "bearer"}


async def current_user(
    token: str = Depends(oauth2), session: AsyncSession = Depends(get_session)
) -> User:
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user_id = UUID(claims["sub"])
        org_id = UUID(claims["org"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    user = await session.scalar(
        select(User)
        .join(Organization, Organization.id == User.organization_id)
        .where(
            User.id == user_id,
            User.organization_id == org_id,
            Organization.active.is_(True),
        )
    )
    if not user or not user.active:
        raise HTTPException(status_code=401, detail="Account is disabled or unavailable")
    return user


@router.get("/me")
async def who_am_i(user: User = Depends(current_user)) -> dict[str, str]:
    return {"id": str(user.id), "name": user.name, "email": user.email, "role": user.role.value}
