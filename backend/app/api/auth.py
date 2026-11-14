from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.models.entities import Organization, User

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
password_hash = PasswordHash.recommended()


class Login(BaseModel):
    email: EmailStr
    password: str
    organization_id: UUID


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
