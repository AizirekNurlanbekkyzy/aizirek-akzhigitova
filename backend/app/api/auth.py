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
    organization_id: UUID

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str) -> str:
        return normalize_email(value)


class Registration(BaseModel):
    email: str
    name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=12, max_length=128)
    organization_id: UUID

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, value: str) -> str:
        return normalize_email(value)


@router.post("/register", status_code=201)
async def register(
    data: Registration, session: AsyncSession = Depends(get_session)
) -> dict[str, str]:
    organization = await session.scalar(
        select(Organization).where(
            Organization.id == data.organization_id, Organization.active.is_(True)
        )
    )
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    user = User(
        organization_id=organization.id,
        email=data.email,
        password_hash=password_hash.hash(data.password),
        name=data.name.strip(),
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
    result = await session.execute(
        select(User)
        .join(Organization, Organization.id == User.organization_id)
        .where(
            User.email == str(data.email).lower(),
            User.organization_id == data.organization_id,
            Organization.active.is_(True),
        )
    )
    user = result.scalar_one_or_none()
    if not user or not user.active or not password_hash.verify(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
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
