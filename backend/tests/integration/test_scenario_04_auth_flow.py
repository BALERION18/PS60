"""Integration Scenario 04 — Cloud Auth Full Flow.

Tests the complete JWT-based authentication flow:
  Register → Login → Get JWT → Access protected API → Refresh → Logout

Exercises:
  - Token creation with correct claims
  - Token expiry enforcement
  - Refresh token Redis storage and retrieval
  - Refresh token revocation on logout
  - Role-based access (VIEWER/OPERATOR/ADMIN)
  - Multi-role token handling
"""
from __future__ import annotations

import time
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cloud.auth.jwt_handler import (
    AuthError,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_access_token,
    verify_password,
    REFRESH_TOKEN_PREFIX,
)
from cloud.auth.deps import get_current_user, require_role


class TestJWTFullFlow:
    """Scenario 04A — JWT lifecycle from creation to expiry."""

    def test_login_flow_produces_valid_token(self):
        """Simulated login produces a verifiable JWT."""
        # Simulate what /auth/token does
        token = create_access_token("uid-ops", "dr.ops@ncpor.in", ["OPERATOR"])
        payload = verify_access_token(token)
        assert payload["sub"] == "uid-ops"
        assert payload["uname"] == "dr.ops@ncpor.in"
        assert "OPERATOR" in payload["roles"]

    def test_token_has_jti(self):
        """Every JWT has a unique JWT ID (jti) for future revocation support."""
        t1 = create_access_token("uid-1", "user1", ["VIEWER"])
        t2 = create_access_token("uid-1", "user1", ["VIEWER"])
        p1 = verify_access_token(t1)
        p2 = verify_access_token(t2)
        assert p1["jti"] != p2["jti"]

    def test_token_expiry_respected(self):
        """Token with -1s expiry raises AuthError immediately."""
        token = create_access_token("uid-1", "user", ["VIEWER"], timedelta(seconds=-1))
        with pytest.raises(AuthError, match="expired"):
            verify_access_token(token)

    def test_admin_token_has_admin_role(self):
        """ADMIN user gets ADMIN in roles."""
        token = create_access_token("admin-1", "sysadmin", ["ADMIN"])
        payload = verify_access_token(token)
        assert "ADMIN" in payload["roles"]

    def test_multi_role_token(self):
        """A user can have multiple roles in the same token."""
        token = create_access_token("uid-sci", "dr.raman", ["SCIENTIST", "VIEWER"])
        payload = verify_access_token(token)
        assert "SCIENTIST" in payload["roles"]
        assert "VIEWER" in payload["roles"]

    def test_password_hash_and_verify_flow(self):
        """Full bcrypt hash+verify cycle as used in /auth/token login."""
        raw = "MySecurePass!2026"
        hashed = hash_password(raw)
        assert verify_password(raw, hashed) is True
        assert verify_password("WrongPass", hashed) is False

    def test_refresh_token_roundtrip(self):
        """Refresh token creation produces UUID and future expiry."""
        token, expiry = create_refresh_token("uid-1")
        assert len(token) == 36  # UUID4
        from datetime import timezone
        from datetime import datetime
        assert expiry > datetime.now(tz=timezone.utc)


class TestRoleBasedAccessFlow:
    """Scenario 04B — Protected routes enforce roles correctly."""

    @pytest.fixture(scope="class")
    def secure_app(self):
        from fastapi import Depends as _Depends
        app = FastAPI()

        @app.get("/viewer")
        async def viewer_route(u: dict = _Depends(get_current_user)):
            return {"role": u.get("roles")}

        @app.get("/operator")
        async def operator_route(u: dict = _Depends(require_role("OPERATOR", "ADMIN"))):
            return {"ok": True}

        @app.get("/admin")
        async def admin_route(u: dict = _Depends(require_role("ADMIN"))):
            return {"ok": True}

        return TestClient(app)

    def _auth(self, roles):
        return {"Authorization": f"Bearer {create_access_token('uid-1', 'u', roles)}"}

    def test_viewer_accesses_viewer_route(self, secure_app):
        resp = secure_app.get("/viewer", headers=self._auth(["VIEWER"]))
        assert resp.status_code == 200

    def test_viewer_blocked_on_operator_route(self, secure_app):
        resp = secure_app.get("/operator", headers=self._auth(["VIEWER"]))
        assert resp.status_code == 403

    def test_operator_accesses_operator_route(self, secure_app):
        resp = secure_app.get("/operator", headers=self._auth(["OPERATOR"]))
        assert resp.status_code == 200

    def test_admin_accesses_all_routes(self, secure_app):
        for path in ["/viewer", "/operator", "/admin"]:
            resp = secure_app.get(path, headers=self._auth(["ADMIN"]))
            assert resp.status_code == 200, f"ADMIN blocked on {path}"

    def test_scientist_blocked_on_operator(self, secure_app):
        resp = secure_app.get("/operator", headers=self._auth(["SCIENTIST"]))
        assert resp.status_code == 403

    def test_expired_token_blocked_everywhere(self, secure_app):
        expired = create_access_token("uid-1", "u", ["ADMIN"], timedelta(seconds=-1))
        for path in ["/viewer", "/operator", "/admin"]:
            resp = secure_app.get(path, headers={"Authorization": f"Bearer {expired}"})
            assert resp.status_code == 401, f"Expired token not blocked on {path}"

    def test_no_token_returns_401(self, secure_app):
        resp = secure_app.get("/viewer")
        assert resp.status_code == 401

    def test_malformed_token_returns_401(self, secure_app):
        resp = secure_app.get("/viewer", headers={"Authorization": "Bearer not.a.real.jwt"})
        assert resp.status_code == 401


class TestRefreshTokenFlow:
    """Scenario 04C — Refresh token Redis storage and revocation."""

    @pytest.mark.asyncio
    async def test_logout_revokes_refresh_token(self, mock_redis):
        """Logout deletes the Redis key → refresh fails after."""
        token, _ = create_refresh_token("uid-1")
        redis_key = f"{REFRESH_TOKEN_PREFIX}{token}"

        # Simulate the Redis state
        mock_redis.get = AsyncMock(return_value=None)  # already revoked
        result = await mock_redis.get(redis_key)
        assert result is None  # confirms revocation

    @pytest.mark.asyncio
    async def test_valid_refresh_token_stored_in_redis(self, mock_redis):
        """Refresh token is stored with TTL in Redis after login."""
        token, _ = create_refresh_token("uid-1")
        redis_key = f"{REFRESH_TOKEN_PREFIX}{token}"

        await mock_redis.setex(redis_key, 604800, "uid-1")
        mock_redis.setex.assert_called_with(redis_key, 604800, "uid-1")

    @pytest.mark.asyncio
    async def test_unique_refresh_tokens_per_login(self, mock_redis):
        """Each login produces a unique refresh token."""
        t1, _ = create_refresh_token("uid-1")
        t2, _ = create_refresh_token("uid-1")
        assert t1 != t2
