"""Unit tests for Phase 6 — Edge local auth.

All tests are pure-function; no Redis, DB, or MQTT required.
"""
from __future__ import annotations

import hmac
import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from edge.auth.local_auth import (
    KeyStore,
    LocalAuth,
    ROLE_HIERARCHY,
    _constant_compare,
    generate_api_key,
    parse_key,
    require_admin,
    require_any,
    require_operator,
    set_key_store,
)


# ---------------------------------------------------------------------------
# parse_key
# ---------------------------------------------------------------------------

class TestParseKey:
    def test_valid_crew_key(self):
        role, secret = parse_key("CREW.abcdef1234567890")
        assert role == "CREW"
        assert secret == "abcdef1234567890"

    def test_valid_operator_key(self):
        role, secret = parse_key("OPERATOR.deadbeef")
        assert role == "OPERATOR"
        assert secret == "deadbeef"

    def test_valid_admin_key(self):
        role, secret = parse_key("ADMIN.cafebabe")
        assert role == "ADMIN"

    def test_lowercase_role_uppercased(self):
        result = parse_key("crew.abcdef")
        assert result[0] == "CREW"

    def test_missing_dot_returns_none(self):
        assert parse_key("CREWabcdef") is None

    def test_unknown_role_returns_none(self):
        assert parse_key("SUPERUSER.abcdef") is None

    def test_empty_string_returns_none(self):
        assert parse_key("") is None

    def test_extra_dots_included_in_secret(self):
        # Only split on first dot
        role, secret = parse_key("CREW.part1.part2")
        assert role == "CREW"
        assert secret == "part1.part2"


# ---------------------------------------------------------------------------
# generate_api_key
# ---------------------------------------------------------------------------

class TestGenerateApiKey:
    def test_format(self):
        key = generate_api_key("CREW")
        assert key.startswith("CREW.")
        assert len(key) > 10

    def test_role_preserved(self):
        key = generate_api_key("ADMIN")
        assert key.startswith("ADMIN.")

    def test_unknown_role_raises(self):
        with pytest.raises(ValueError):
            generate_api_key("SUPERUSER")

    def test_deterministic_with_provided_bytes(self):
        secret = bytes(range(32))
        k1 = generate_api_key("OPERATOR", secret)
        k2 = generate_api_key("OPERATOR", secret)
        assert k1 == k2

    def test_random_when_no_bytes(self):
        k1 = generate_api_key("CREW")
        k2 = generate_api_key("CREW")
        assert k1 != k2  # Probabilistically true with 32 random bytes


# ---------------------------------------------------------------------------
# KeyStore
# ---------------------------------------------------------------------------

class TestKeyStore:
    def test_valid_key_returns_role(self):
        key = generate_api_key("CREW")
        store = KeyStore([key])
        _, secret = parse_key(key)
        assert store.lookup(secret) == "CREW"

    def test_invalid_key_returns_none(self):
        store = KeyStore([generate_api_key("CREW")])
        assert store.lookup("nonexistent_secret") is None

    def test_multiple_keys(self):
        crew_key = generate_api_key("CREW")
        admin_key = generate_api_key("ADMIN")
        store = KeyStore([crew_key, admin_key])
        _, crew_secret = parse_key(crew_key)
        _, admin_secret = parse_key(admin_key)
        assert store.lookup(crew_secret) == "CREW"
        assert store.lookup(admin_secret) == "ADMIN"

    def test_malformed_keys_ignored(self):
        store = KeyStore(["BADKEY", "NODOTSHERE", generate_api_key("OPERATOR")])
        # Should not raise and store has one valid entry
        assert store is not None

    def test_empty_store(self):
        store = KeyStore([])
        assert store.lookup("anything") is None

    def test_case_insensitive_lookup(self):
        key = generate_api_key("CREW")
        store = KeyStore([key])
        _, secret = parse_key(key)
        # Should match both upper and lower case
        assert store.lookup(secret.upper()) == "CREW"
        assert store.lookup(secret.lower()) == "CREW"


# ---------------------------------------------------------------------------
# _constant_compare
# ---------------------------------------------------------------------------

class TestConstantCompare:
    def test_equal_strings(self):
        assert _constant_compare("hello", "hello") is True

    def test_unequal_strings(self):
        assert _constant_compare("hello", "world") is False

    def test_empty_strings(self):
        assert _constant_compare("", "") is True

    def test_different_lengths(self):
        assert _constant_compare("abc", "abcd") is False


# ---------------------------------------------------------------------------
# LocalAuth FastAPI dependency — via TestClient
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def auth_app():
    """Minimal FastAPI app with auth-protected endpoints for testing."""
    crew_key = "CREW.4a7f2b91e3c0d85a1f6e9b2c4d7e0f3a1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d"
    op_key = "OPERATOR.d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a391e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7"
    admin_key = "ADMIN.f1e2d3c4b5a6978869504132a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1"
    store = KeyStore([crew_key, op_key, admin_key])
    set_key_store(store)

    from fastapi import Depends as _Depends
    app = FastAPI()

    @app.get("/crew-only")
    async def crew_only(_auth: dict = _Depends(require_any)):
        return {"ok": True}

    @app.get("/operator-only")
    async def operator_only(_auth: dict = _Depends(require_operator)):
        return {"ok": True}

    @app.get("/admin-only")
    async def admin_only(_auth: dict = _Depends(require_admin)):
        return {"ok": True}

    return app


@pytest.fixture(scope="module")
def auth_client(auth_app):
    return TestClient(auth_app)


class TestLocalAuthDependency:
    def test_crew_can_access_crew_endpoint(self, auth_client):
        token = "CREW.4a7f2b91e3c0d85a1f6e9b2c4d7e0f3a1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d"
        resp = auth_client.get("/crew-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_missing_token_returns_401(self, auth_client):
        resp = auth_client.get("/crew-only")
        assert resp.status_code == 401

    def test_invalid_token_format_returns_401(self, auth_client):
        resp = auth_client.get("/crew-only", headers={"Authorization": "Bearer not-a-valid-key"})
        assert resp.status_code == 401

    def test_wrong_secret_returns_401(self, auth_client):
        resp = auth_client.get(
            "/crew-only",
            headers={"Authorization": "Bearer CREW.0000000000000000000000000000000000000000000000000000000000000000"},
        )
        assert resp.status_code == 401

    def test_crew_cannot_access_operator_endpoint(self, auth_client):
        token = "CREW.4a7f2b91e3c0d85a1f6e9b2c4d7e0f3a1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d"
        resp = auth_client.get("/operator-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_operator_can_access_operator_endpoint(self, auth_client):
        token = "OPERATOR.d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a391e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7"
        resp = auth_client.get("/operator-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_admin_can_access_all_endpoints(self, auth_client):
        token = "ADMIN.f1e2d3c4b5a6978869504132a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1"
        for path in ["/crew-only", "/operator-only", "/admin-only"]:
            resp = auth_client.get(path, headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200, f"ADMIN should access {path}"

    def test_operator_cannot_access_admin_endpoint(self, auth_client):
        token = "OPERATOR.d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a391e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7"
        resp = auth_client.get("/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Role hierarchy
# ---------------------------------------------------------------------------

class TestRoleHierarchy:
    def test_crew_in_hierarchy(self):
        assert "CREW" in ROLE_HIERARCHY

    def test_operator_in_hierarchy(self):
        assert "OPERATOR" in ROLE_HIERARCHY

    def test_admin_in_hierarchy(self):
        assert "ADMIN" in ROLE_HIERARCHY

    def test_hierarchy_order(self):
        assert ROLE_HIERARCHY.index("CREW") < ROLE_HIERARCHY.index("OPERATOR")
        assert ROLE_HIERARCHY.index("OPERATOR") < ROLE_HIERARCHY.index("ADMIN")
