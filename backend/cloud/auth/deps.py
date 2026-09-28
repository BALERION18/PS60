"""FastAPI dependency providers for Cloud JWT authentication.

Usage in routes:
    @router.get("/protected")
    async def protected(principal = Depends(get_current_user)):
        ...

    @router.get("/admin-only")
    async def admin_only(principal = Depends(require_role("ADMIN"))):
        ...

Principal dict:
    {"sub": user_id, "uname": username, "roles": ["ADMIN"], ...}
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from cloud.auth.jwt_handler import AuthError, verify_access_token

log = structlog.get_logger(__name__)

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Dict[str, Any]:
    """Extract and validate the JWT from the Authorization header.

    Returns:
        The decoded JWT payload (principal dict).

    Raises:
        401 if token is missing or invalid.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Use: Bearer <jwt>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = verify_access_token(credentials.credentials)
        return payload
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(*roles: str) -> Callable:
    """Factory — returns a dependency that ensures the principal has one of the given roles.

    Usage:
        @router.delete("/station/{id}", dependencies=[Depends(require_role("ADMIN"))])
    """
    allowed = {r.upper() for r in roles}

    async def _check(
        principal: Dict[str, Any] = Depends(get_current_user),
    ) -> Dict[str, Any]:
        user_roles: List[str] = [r.upper() for r in principal.get("roles", [])]
        if not any(r in allowed for r in user_roles):
            log.warning(
                "cloud.auth.forbidden",
                username=principal.get("uname"),
                user_roles=user_roles,
                required=list(allowed),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of roles {sorted(allowed)} is required for this endpoint",
            )
        return principal

    return _check


# Pre-built role guards for convenience
require_admin = require_role("ADMIN")
require_operator = require_role("OPERATOR", "ADMIN")
require_any_user = get_current_user
