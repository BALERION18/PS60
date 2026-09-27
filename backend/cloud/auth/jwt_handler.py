"""JWT token creation and verification for the Cloud HQ API.

Uses HS256 with a secret key (CLOUD_JWT_SECRET env var).
For production, replace with RS256 and a proper PKI.

Token structure:
  {
    "sub":   "<user_id>",
    "uname": "<username>",
    "roles": ["ADMIN"],
    "exp":   <unix_timestamp>,
    "iat":   <unix_timestamp>,
    "jti":   "<uuid4>",        # JWT ID — for future revocation list support
  }

Refresh tokens are longer-lived (default 7 days) and stored as opaque
references in Redis; they are exchanged for new access tokens via
POST /api/v1/auth/refresh.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import jwt
import structlog

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_SECRET_KEY = os.environ.get("CLOUD_JWT_SECRET", "dev-insecure-secret-change-in-prod-!!!")
_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("JWT_ACCESS_EXPIRE_MINUTES", "60"))
_REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("JWT_REFRESH_EXPIRE_DAYS", "7"))

# Redis key prefix for refresh token allowlist
REFRESH_TOKEN_PREFIX = "cloud:refresh_token:"


class AuthError(Exception):
    """Raised when token creation or validation fails."""


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------

def create_access_token(
    user_id: str,
    username: str,
    roles: List[str],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(tz=timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES))
    payload: Dict[str, Any] = {
        "sub": user_id,
        "uname": username,
        "roles": roles,
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


def create_refresh_token(user_id: str) -> tuple[str, datetime]:
    """Create an opaque refresh token (UUID) and its expiry.

    Returns:
        (token_str, expiry_datetime)
    """
    token = str(uuid.uuid4())
    expiry = datetime.now(tz=timezone.utc) + timedelta(days=_REFRESH_TOKEN_EXPIRE_DAYS)
    return token, expiry


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------

def verify_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token.

    Returns:
        The decoded payload dict.

    Raises:
        AuthError: If the token is expired, malformed, or has an invalid signature.
    """
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError("Access token has expired")
    except jwt.InvalidTokenError as exc:
        raise AuthError(f"Invalid access token: {exc}")


# ---------------------------------------------------------------------------
# Password hashing (bcrypt via passlib)
# ---------------------------------------------------------------------------

try:
    from passlib.context import CryptContext
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(plain: str) -> str:
        return _pwd_context.hash(plain)

    def verify_password(plain: str, hashed: str) -> bool:
        return _pwd_context.verify(plain, hashed)

except ImportError:
    # Fallback for test environments without passlib
    import hashlib

    def hash_password(plain: str) -> str:   # type: ignore[misc]
        return "sha256:" + hashlib.sha256(plain.encode()).hexdigest()

    def verify_password(plain: str, hashed: str) -> bool:  # type: ignore[misc]
        if hashed.startswith("sha256:"):
            return hashlib.sha256(plain.encode()).hexdigest() == hashed[7:]
        return False
