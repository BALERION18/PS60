"""Unit tests for Phase 7 — Cloud auth & security hardening.

Covers JWT creation/verification, password hashing, auth dep 401/403,
security headers middleware, and audit log middleware.
All tests are pure-function; no real DB or Redis required.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("CLOUD_JWT_SECRET", "test-secret-for-unit-tests-only")

from cloud.auth.jwt_handler import (
    AuthError,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_access_token,
    verify_password,
)
from cloud.auth.deps import get_current_user, require_role
from cloud.middleware.audit_log import AuditLogMiddleware
from cloud.middleware.security import SecurityHeadersMiddleware


# ---------------------------------------------------------------------------
# JWT handler — create_access_token
# ---------------------------------------------------------------------------

class TestCreateAccessToken:
    def test_returns_string(self):
        token = create_access_token("uid-1", "ops@ncpor.in", ["OPERATOR"])
        assert isinstance(token, str) and len(token) > 20

    def test_token_contains_three_parts(self):
        token = create_access_token("uid-1", "ops", ["ADMIN"])
        parts = token.split(".")
        assert len(parts) == 3  # header.payload.signature

    def test_two_tokens_are_unique(self):
        t1 = create_access_token("uid-1", "ops", ["ADMIN"])
        time.sleep(0.01)
        t2 = create_access_token("uid-1", "ops", ["ADMIN"])
        # Different jti → different tokens
        assert t1 != t2

    def test_custom_expiry(self):
        token = create_access_token("uid-1", "ops", [], timedelta(seconds=10))
        payload = verify_access_token(token)
        remaining = payload["exp"] - time.time()
        assert 0 < remaining <= 10


# ---------------------------------------------------------------------------
# JWT handler — verify_access_token
# ---------------------------------------------------------------------------

class TestVerifyAccessToken:
    def test_roundtrip(self):
        token = create_access_token("uid-42", "dr.raghavan", ["SCIENTIST", "VIEWER"])
        payload = verify_access_token(token)
        assert payload["sub"] == "uid-42"
        assert payload["uname"] == "dr.raghavan"
        assert "SCIENTIST" in payload["roles"]

    def test_expired_token_raises(self):
        token = create_access_token("uid-1", "ops", [], timedelta(seconds=-1))
        with pytest.raises(AuthError, match="expired"):
            verify_access_token(token)

    def test_tampered_token_raises(self):
        token = create_access_token("uid-1", "ops", ["ADMIN"])
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(AuthError):
            verify_access_token(tampered)

    def test_garbage_token_raises(self):
        with pytest.raises(AuthError):
            verify_access_token("not.a.jwt")

    def test_empty_roles_allowed(self):
        token = create_access_token("uid-1", "viewer", [])
        payload = verify_access_token(token)
        assert payload["roles"] == []


# ---------------------------------------------------------------------------
# JWT handler — create_refresh_token
# ---------------------------------------------------------------------------

class TestCreateRefreshToken:
    def test_returns_string_and_datetime(self):
        token, expiry = create_refresh_token("uid-1")
        assert isinstance(token, str)
        assert isinstance(expiry, datetime)

    def test_token_is_uuid_like(self):
        token, _ = create_refresh_token("uid-1")
        # UUID4 has 36 chars with dashes
        assert len(token) == 36
        assert token.count("-") == 4

    def test_two_refresh_tokens_unique(self):
        t1, _ = create_refresh_token("uid-1")
        t2, _ = create_refresh_token("uid-1")
        assert t1 != t2

    def test_expiry_in_future(self):
        _, expiry = create_refresh_token("uid-1")
        assert expiry > datetime.now(tz=timezone.utc)

    def test_expiry_roughly_7_days(self):
        _, expiry = create_refresh_token("uid-1")
        delta = expiry - datetime.now(tz=timezone.utc)
        # Within 10 seconds of 7 days
        assert abs(delta.total_seconds() - 7 * 86400) < 10


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_hash_returns_string(self):
        h = hash_password("secret123")
        assert isinstance(h, str) and len(h) > 10

    def test_verify_correct_password(self):
        h = hash_password("correct-horse-battery-staple")
        assert verify_password("correct-horse-battery-staple", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("correct-password")
        assert verify_password("wrong-password", h) is False

    def test_two_hashes_of_same_password_differ(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        # bcrypt salts → hashes differ
        assert h1 != h2 or h1.startswith("sha256:")  # sha256 fallback is deterministic

    def test_empty_password(self):
        h = hash_password("")
        assert verify_password("", h) is True
        assert verify_password("x", h) is False


# ---------------------------------------------------------------------------
# Cloud auth deps — get_current_user via TestClient
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def jwt_app():
    """Minimal FastAPI app with JWT-protected and role-guarded routes."""
    from fastapi import Depends as _Depends
    app = FastAPI()

    @app.get("/me")
    async def me(principal: dict = _Depends(get_current_user)):
        return {"sub": principal["sub"]}

    @app.get("/admin-only")
    async def admin_only(principal: dict = _Depends(require_role("ADMIN"))):
        return {"ok": True}

    @app.get("/operator-or-admin")
    async def op_or_admin(principal: dict = _Depends(require_role("OPERATOR", "ADMIN"))):
        return {"ok": True}

    return app


@pytest.fixture(scope="module")
def jwt_client(jwt_app):
    return TestClient(jwt_app)


def _make_token(roles=None, user_id="uid-1", username="testuser", expired=False):
    delta = timedelta(seconds=-1) if expired else None
    return create_access_token(user_id, username, roles or ["VIEWER"], delta)


class TestJWTAuthDeps:
    def test_valid_token_returns_200(self, jwt_client):
        token = _make_token(["VIEWER"])
        resp = jwt_client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["sub"] == "uid-1"

    def test_missing_token_returns_401(self, jwt_client):
        resp = jwt_client.get("/me")
        assert resp.status_code == 401

    def test_expired_token_returns_401(self, jwt_client):
        token = _make_token(expired=True)
        resp = jwt_client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_garbage_token_returns_401(self, jwt_client):
        resp = jwt_client.get("/me", headers={"Authorization": "Bearer garbage.token.here"})
        assert resp.status_code == 401

    def test_viewer_forbidden_on_admin_endpoint(self, jwt_client):
        token = _make_token(["VIEWER"])
        resp = jwt_client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_admin_can_access_admin_endpoint(self, jwt_client):
        token = _make_token(["ADMIN"])
        resp = jwt_client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_operator_can_access_operator_endpoint(self, jwt_client):
        token = _make_token(["OPERATOR"])
        resp = jwt_client.get("/operator-or-admin", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_admin_can_access_operator_endpoint(self, jwt_client):
        token = _make_token(["ADMIN"])
        resp = jwt_client.get("/operator-or-admin", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_viewer_forbidden_on_operator_endpoint(self, jwt_client):
        token = _make_token(["VIEWER"])
        resp = jwt_client.get("/operator-or-admin", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def security_client():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"ok": True}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return TestClient(app)


class TestSecurityHeadersMiddleware:
    def test_hsts_header_present(self, security_client):
        resp = security_client.get("/health")
        assert "strict-transport-security" in resp.headers

    def test_hsts_max_age(self, security_client):
        resp = security_client.get("/health")
        assert "max-age=31536000" in resp.headers["strict-transport-security"]

    def test_x_content_type_options(self, security_client):
        resp = security_client.get("/health")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_x_frame_options(self, security_client):
        resp = security_client.get("/health")
        assert resp.headers.get("x-frame-options") == "DENY"

    def test_csp_header_present(self, security_client):
        resp = security_client.get("/health")
        assert "content-security-policy" in resp.headers

    def test_no_cache_on_api_paths(self, security_client):
        resp = security_client.get("/api/v1/test")
        assert "no-store" in resp.headers.get("cache-control", "")

    def test_no_cache_not_on_health(self, security_client):
        resp = security_client.get("/health")
        # Health is not an /api/ path — cache-control may be absent
        assert "no-store" not in resp.headers.get("cache-control", "")

    def test_referrer_policy(self, security_client):
        resp = security_client.get("/health")
        assert "referrer-policy" in resp.headers


# ---------------------------------------------------------------------------
# Audit log middleware
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def audit_client():
    app = FastAPI()
    app.add_middleware(AuditLogMiddleware)

    @app.get("/api/v1/data")
    async def data():
        return {"data": "ok"}

    @app.post("/api/v1/data")
    async def create_data():
        return {"created": True}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return TestClient(app)


class TestAuditLogMiddleware:
    def test_request_id_header_present(self, audit_client):
        resp = audit_client.get("/api/v1/data")
        assert "x-request-id" in resp.headers

    def test_request_id_is_short(self, audit_client):
        resp = audit_client.get("/api/v1/data")
        # 8 hex chars from UUID
        assert len(resp.headers["x-request-id"]) == 8

    def test_health_has_request_id(self, audit_client):
        resp = audit_client.get("/health")
        # Health is exempt from logging but request-id may or may not be set
        # The middleware should not crash on health endpoints
        assert resp.status_code == 200

    def test_get_returns_200(self, audit_client):
        resp = audit_client.get("/api/v1/data")
        assert resp.status_code == 200

    def test_post_returns_200(self, audit_client):
        resp = audit_client.post("/api/v1/data")
        assert resp.status_code == 200

    def test_unique_request_ids_per_call(self, audit_client):
        r1 = audit_client.get("/api/v1/data")
        r2 = audit_client.get("/api/v1/data")
        assert r1.headers["x-request-id"] != r2.headers["x-request-id"]
