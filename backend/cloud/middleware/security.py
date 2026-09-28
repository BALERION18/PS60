"""Security headers middleware for the Cloud HQ API.

Adds hardened HTTP response headers to every response:
  - Strict-Transport-Security (HSTS) — enforces HTTPS
  - Content-Security-Policy        — restricts resource loading
  - X-Content-Type-Options         — prevents MIME sniffing
  - X-Frame-Options                — prevents clickjacking
  - X-XSS-Protection               — legacy XSS filter
  - Referrer-Policy                — limits referrer leakage
  - Permissions-Policy             — restricts browser features
  - Cache-Control                  — prevents sensitive data caching

These are defence-in-depth headers. FastAPI/Starlette CORS middleware
handles CORS separately.
"""
from __future__ import annotations

from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds hardened HTTP security headers to every response."""

    def __init__(self, app: ASGIApp, hsts_max_age: int = 31536000) -> None:
        super().__init__(app)
        self._hsts_max_age = hsts_max_age

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        response.headers["Strict-Transport-Security"] = (
            f"max-age={self._hsts_max_age}; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self' wss:; "
            "frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), camera=(), microphone=()"
        )
        # Prevent caching of API responses (may contain sensitive operational data)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, max-age=0"
            response.headers["Pragma"] = "no-cache"

        return response
