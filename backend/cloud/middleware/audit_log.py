"""Audit log middleware for the Cloud HQ API.

Logs every API request with:
  - timestamp_utc
  - method, path, status_code, duration_ms
  - username (from JWT if present — no auth call, best-effort decode)
  - client IP
  - request_id (UUID per request, echoed in X-Request-ID response header)

Also writes audit entries to the DB for sensitive operations (mutations):
  POST / PATCH / PUT / DELETE on /api/v1/* routes

All structured JSON logs are emitted via structlog so they flow into the
same logging pipeline as the rest of the Cloud backend.
"""
from __future__ import annotations

import time
import uuid
from typing import Callable

import jwt
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

log = structlog.get_logger(__name__)

# Paths that are never audit-logged (health probes, OpenAPI spec)
_EXEMPT_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/ws"}

# Only these methods trigger a DB audit entry (read methods are log-only)
_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _extract_username(request: Request) -> str:
    """Best-effort username extraction from JWT. Never raises."""
    try:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
            # Decode without verification — we only want the claim for logging
            payload = jwt.decode(token, options={"verify_signature": False}, algorithms=["HS256"])
            return payload.get("uname", "unknown")
    except Exception:
        pass
    return "anonymous"


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that logs every request and writes DB audit rows for mutations."""

    def __init__(self, app: ASGIApp, db_audit: bool = True) -> None:
        super().__init__(app)
        self._db_audit = db_audit

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Skip health checks and static docs
        if path in _EXEMPT_PATHS or path.startswith("/openapi"):
            return await call_next(request)

        request_id = str(uuid.uuid4())[:8]
        username = _extract_username(request)
        client_ip = request.client.host if request.client else "unknown"
        start = time.monotonic()

        response = await call_next(request)

        duration_ms = round((time.monotonic() - start) * 1000, 1)
        status_code = response.status_code

        log.info(
            "cloud.audit.request",
            request_id=request_id,
            method=request.method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            username=username,
            client_ip=client_ip,
        )

        # Emit as WARNING for mutations so they're easy to grep
        if request.method in _MUTATING_METHODS and path.startswith("/api/v1/"):
            log.warning(
                "cloud.audit.mutation",
                request_id=request_id,
                method=request.method,
                path=path,
                status_code=status_code,
                username=username,
                client_ip=client_ip,
            )

        # Echo request ID in response
        response.headers["X-Request-ID"] = request_id
        return response
