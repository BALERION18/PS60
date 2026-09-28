"""Toxiproxy REST API client for the VajraX satellite link simulator.

Toxiproxy (https://github.com/Shopify/toxiproxy) is a TCP proxy that
allows injecting network failure modes: latency, bandwidth limits,
connection drops. We use it as the satellite link simulation layer.

Each station's sync agent connects to toxiproxy, which forwards to
the Cloud MQTT broker. Toxics are added/removed via toxiproxy's REST API.

This client wraps the toxiproxy REST API with a clean async interface.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx
import structlog

log = structlog.get_logger(__name__)

TOXIPROXY_HOST = os.getenv("TOXIPROXY_HOST", "localhost")
TOXIPROXY_API_PORT = int(os.getenv("TOXIPROXY_API_PORT", "8474"))
TOXIPROXY_BASE_URL = f"http://{TOXIPROXY_HOST}:{TOXIPROXY_API_PORT}"


class ToxiproxyClient:
    """Async client for the toxiproxy REST API."""

    def __init__(self, base_url: str = TOXIPROXY_BASE_URL) -> None:
        self.base_url = base_url
        self._client = httpx.AsyncClient(timeout=5.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def list_proxies(self) -> Dict[str, Any]:
        resp = await self._client.get(f"{self.base_url}/proxies")
        resp.raise_for_status()
        return resp.json()

    async def create_proxy(
        self,
        name: str,
        listen: str,
        upstream: str,
        enabled: bool = True,
    ) -> Dict[str, Any]:
        """Create a new proxy.

        Args:
            name: Unique proxy name (e.g., "maitri-mqtt").
            listen: Listen address (e.g., "0.0.0.0:18883").
            upstream: Upstream address to proxy to (e.g., "mosquitto-cloud:8883").
            enabled: Whether traffic flows initially.
        """
        payload = {"name": name, "listen": listen, "upstream": upstream, "enabled": enabled}
        resp = await self._client.post(f"{self.base_url}/proxies", json=payload)
        resp.raise_for_status()
        log.info("link_sim.proxy_created", name=name, listen=listen, upstream=upstream)
        return resp.json()

    async def delete_proxy(self, name: str) -> None:
        resp = await self._client.delete(f"{self.base_url}/proxies/{name}")
        if resp.status_code != 404:
            resp.raise_for_status()

    async def enable_proxy(self, name: str) -> None:
        """Enable (restore) a proxy — resumes traffic flow."""
        resp = await self._client.post(
            f"{self.base_url}/proxies/{name}",
            json={"enabled": True},
        )
        resp.raise_for_status()
        log.info("link_sim.link_up", proxy=name)

    async def disable_proxy(self, name: str) -> None:
        """Disable a proxy — drops all connections (simulates link outage)."""
        resp = await self._client.post(
            f"{self.base_url}/proxies/{name}",
            json={"enabled": False},
        )
        resp.raise_for_status()
        log.info("link_sim.link_down", proxy=name)

    async def add_latency_toxic(
        self,
        proxy_name: str,
        latency_ms: int = 800,
        jitter_ms: int = 200,
        direction: str = "downstream",
        toxic_name: str = "satellite_latency",
    ) -> Dict[str, Any]:
        """Add a latency toxic simulating satellite round-trip delay."""
        payload = {
            "name": toxic_name,
            "type": "latency",
            "stream": direction,
            "toxicity": 1.0,
            "attributes": {"latency": latency_ms, "jitter": jitter_ms},
        }
        resp = await self._client.post(
            f"{self.base_url}/proxies/{proxy_name}/toxics",
            json=payload,
        )
        resp.raise_for_status()
        log.info("link_sim.latency_added", proxy=proxy_name,
                 latency_ms=latency_ms, jitter_ms=jitter_ms)
        return resp.json()

    async def add_bandwidth_toxic(
        self,
        proxy_name: str,
        rate_kbps: int = 512,
        direction: str = "downstream",
        toxic_name: str = "satellite_bandwidth",
    ) -> Dict[str, Any]:
        """Add a bandwidth throttle toxic (simulates constrained satellite link)."""
        payload = {
            "name": toxic_name,
            "type": "bandwidth",
            "stream": direction,
            "toxicity": 1.0,
            "attributes": {"rate": rate_kbps},
        }
        resp = await self._client.post(
            f"{self.base_url}/proxies/{proxy_name}/toxics",
            json=payload,
        )
        resp.raise_for_status()
        log.info("link_sim.bandwidth_throttle_added", proxy=proxy_name, rate_kbps=rate_kbps)
        return resp.json()

    async def remove_toxic(self, proxy_name: str, toxic_name: str) -> None:
        """Remove a named toxic from a proxy."""
        resp = await self._client.delete(
            f"{self.base_url}/proxies/{proxy_name}/toxics/{toxic_name}"
        )
        if resp.status_code != 404:
            resp.raise_for_status()
        log.info("link_sim.toxic_removed", proxy=proxy_name, toxic=toxic_name)

    async def list_toxics(self, proxy_name: str) -> List[Dict[str, Any]]:
        """List all active toxics on a proxy."""
        resp = await self._client.get(f"{self.base_url}/proxies/{proxy_name}/toxics")
        resp.raise_for_status()
        return resp.json()

    async def reset_proxy(self, proxy_name: str) -> None:
        """Remove all toxics and re-enable the proxy (restore normal link)."""
        toxics = await self.list_toxics(proxy_name)
        for toxic in toxics:
            await self.remove_toxic(proxy_name, toxic["name"])
        await self.enable_proxy(proxy_name)
        log.info("link_sim.proxy_reset", proxy=proxy_name)

    async def health_check(self) -> bool:
        """Return True if toxiproxy is reachable."""
        try:
            resp = await self._client.get(f"{self.base_url}/version")
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False
