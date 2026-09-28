"""Cloud auth endpoints — login, token refresh, and user management.

Routes:
  POST /api/v1/auth/token            Login → access + refresh tokens
  POST /api/v1/auth/refresh          Exchange refresh token → new access token
  POST /api/v1/auth/logout           Revoke refresh token
  GET  /api/v1/auth/me               Current user info
  POST /api/v1/auth/users            Create user (ADMIN only)
  GET  /api/v1/auth/users            List users (ADMIN only)
  DELETE /api/v1/auth/users/{id}     Deactivate user (ADMIN only)

Refresh token flow:
  1. Login → access_token (1h) + refresh_token (opaque UUID, 7d, stored in Redis)
  2. Client sends refresh_token to /refresh → new access_token
  3. /logout → Redis deletes refresh_token (instant revocation)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models.cloud import Role, User, UserRole
from shared.utils.time import utcnow
from cloud.auth.deps import get_current_user, require_admin
from cloud.auth.jwt_handler import (
    REFRESH_TOKEN_PREFIX,
    AuthError,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from cloud.deps import get_db_session
from cloud.redis_client import get_redis

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_REFRESH_TTL_SECONDS = 7 * 24 * 3600


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int   # seconds
    refresh_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class CreateUserRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    roles: List[str] = ["VIEWER"]


class UserOut(BaseModel):
    user_id: str
    username: str
    email: Optional[str]
    is_active: bool
    roles: List[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_user_roles(session: AsyncSession, user_id: str) -> List[str]:
    result = await session.execute(
        select(Role.role_name)
        .join(UserRole, Role.role_id == UserRole.role_id)
        .where(UserRole.user_id == user_id)
    )
    return [row[0] for row in result.all()]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/token", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Authenticate with username + password, receive JWT + refresh token."""
    result = await session.execute(
        select(User).where(User.username == body.username).where(User.is_active == True)
    )
    user: Optional[User] = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        log.warning("cloud.auth.login_failed", username=body.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    roles = await _get_user_roles(session, user.user_id)
    access_token = create_access_token(user.user_id, user.username, roles)

    refresh_token, refresh_expiry = create_refresh_token(user.user_id)
    redis = get_redis()
    await redis.setex(
        f"{REFRESH_TOKEN_PREFIX}{refresh_token}",
        _REFRESH_TTL_SECONDS,
        user.user_id,
    )

    # Update last_login_at
    user.last_login_at = utcnow()
    await session.commit()

    log.info("cloud.auth.login_ok", username=user.username, roles=roles)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AccessTokenResponse:
    """Exchange a valid refresh token for a new access token."""
    redis = get_redis()
    redis_key = f"{REFRESH_TOKEN_PREFIX}{body.refresh_token}"
    user_id_bytes = await redis.get(redis_key)

    if user_id_bytes is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or expired",
        )

    user_id = user_id_bytes.decode() if isinstance(user_id_bytes, bytes) else user_id_bytes
    result = await session.execute(
        select(User).where(User.user_id == user_id).where(User.is_active == True)
    )
    user: Optional[User] = result.scalar_one_or_none()
    if user is None:
        await redis.delete(redis_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    roles = await _get_user_roles(session, user_id)
    access_token = create_access_token(user_id, user.username, roles)

    log.info("cloud.auth.token_refreshed", username=user.username)
    return AccessTokenResponse(access_token=access_token, expires_in=3600)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    body: RefreshRequest,
) -> dict:
    """Revoke a refresh token instantly."""
    redis = get_redis()
    await redis.delete(f"{REFRESH_TOKEN_PREFIX}{body.refresh_token}")
    log.info("cloud.auth.logout")
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserOut)
async def me(
    principal: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> UserOut:
    """Return the current authenticated user's profile."""
    result = await session.execute(
        select(User).where(User.user_id == principal["sub"])
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(404, "User not found")
    roles = await _get_user_roles(session, user.user_id)
    return UserOut(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        roles=roles,
        created_at=user.created_at,
    )


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserRequest,
    _admin: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> UserOut:
    """Create a new user (ADMIN only)."""
    existing = await session.execute(
        select(User).where(User.username == body.username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"Username {body.username!r} already taken")

    user = User(
        user_id=str(uuid.uuid4()),
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        is_active=True,
        created_at=utcnow(),
    )
    session.add(user)
    await session.flush()

    # Assign roles
    for role_name in body.roles:
        role_result = await session.execute(
            select(Role).where(Role.role_name == role_name.upper())
        )
        role = role_result.scalar_one_or_none()
        if role is None:
            role = Role(role_id=str(uuid.uuid4()), role_name=role_name.upper())
            session.add(role)
            await session.flush()
        session.add(UserRole(
            assignment_id=str(uuid.uuid4()),
            user_id=user.user_id,
            role_id=role.role_id,
            assigned_at=utcnow(),
        ))

    await session.commit()
    log.info("cloud.auth.user_created", username=body.username, roles=body.roles)
    return UserOut(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        roles=body.roles,
        created_at=user.created_at,
    )


@router.get("/users", response_model=List[UserOut])
async def list_users(
    _admin: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> List[UserOut]:
    """List all platform users (ADMIN only)."""
    result = await session.execute(select(User).order_by(User.created_at))
    users = result.scalars().all()
    out = []
    for u in users:
        roles = await _get_user_roles(session, u.user_id)
        out.append(UserOut(
            user_id=u.user_id,
            username=u.username,
            email=u.email,
            is_active=u.is_active,
            roles=roles,
            created_at=u.created_at,
        ))
    return out

@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def deactivate_user(
    user_id: str,
    _admin: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Deactivate (soft-delete) a user account (ADMIN only)."""
    result = await session.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(404, f"User {user_id!r} not found")
    user.is_active = False
    await session.commit()
    log.info("cloud.auth.user_deactivated", user_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
