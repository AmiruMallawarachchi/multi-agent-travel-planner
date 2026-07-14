"""
agents/mcp_client.py
The single point of contact between the agent graph and the MCP servers
(SRS section 9-E1: "Adding or swapping a service must not require editing
core agent code").

Two responsibilities live here and nowhere else:
  1. Load tools SCOPED to one server, so the Hotel Agent can physically never
     bind a flight tool and vice versa (SRS section 2 - agent roles).
  2. A small circuit breaker so a dead MCP server degrades this turn's answer
     instead of hanging the request or crashing the conversation
     (SRS section 5 & 7 - resilience is non-negotiable).
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Literal, cast

import httpx
from langchain_mcp_adapters.client import MultiServerMCPClient

ServerName = Literal[
    "hotel-mcp",
    "flight-mcp",
    "itinerary-mcp",
    "weather-mcp",
    "currency-mcp",
    "location-mcp",
]
ServerStatus = Literal["available", "unavailable"]

HOTEL_MCP_URL = os.getenv("HOTEL_MCP_URL", "http://localhost:8001/mcp")
FLIGHT_MCP_URL = os.getenv("FLIGHT_MCP_URL", "http://localhost:8002/mcp")
ITINERARY_MCP_URL = os.getenv("ITINERARY_MCP_URL", "http://localhost:8003/mcp")
WEATHER_MCP_URL = os.getenv("WEATHER_MCP_URL", "http://localhost:8004/mcp")
CURRENCY_MCP_URL = os.getenv("CURRENCY_MCP_URL", "http://localhost:8005/mcp")
LOCATION_MCP_URL = os.getenv("LOCATION_MCP_URL", "http://localhost:8006/mcp")

MCP_SERVER_URLS: dict[ServerName, str] = {
    "hotel-mcp": HOTEL_MCP_URL,
    "flight-mcp": FLIGHT_MCP_URL,
    "itinerary-mcp": ITINERARY_MCP_URL,
    "weather-mcp": WEATHER_MCP_URL,
    "currency-mcp": CURRENCY_MCP_URL,
    "location-mcp": LOCATION_MCP_URL,
}
HEALTH_TIMEOUT = httpx.Timeout(connect=1.0, read=2.0, write=1.0, pool=1.0)
logger = logging.getLogger("tripweaver.mcp")

# After this many consecutive failures, stop hitting the server for a while
# instead of making every traveller wait out a timeout on a server that's down.
BREAKER_FAILURE_THRESHOLD = 3
BREAKER_COOLDOWN_SECONDS = 60


@dataclass
class _Breaker:
    failures: int = 0
    open_until: float = 0.0

    def is_open(self) -> bool:
        return time.monotonic() < self.open_until

    def record_success(self) -> None:
        self.failures = 0
        self.open_until = 0.0

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= BREAKER_FAILURE_THRESHOLD:
            self.open_until = time.monotonic() + BREAKER_COOLDOWN_SECONDS


_breakers: dict[ServerName, _Breaker] = {
    server: _Breaker() for server in MCP_SERVER_URLS
}

# One client owns the service registry while each specialist still loads only
# its explicitly configured server set.
_client = MultiServerMCPClient(
    {
        server: {"url": url, "transport": "http"}
        for server, url in MCP_SERVER_URLS.items()
    }
)


def breaker_open(server: ServerName) -> bool:
    return _breakers[server].is_open()


async def get_tools_for(server: ServerName) -> list:
    """
    Load only `server`'s tools. Never raises: an unreachable server or an
    open circuit breaker both just mean the caller gets an empty tool list
    back and can degrade gracefully (SRS section 5 / 6 / 7) instead of the
    whole turn failing.
    """
    if breaker_open(server):
        return []
    try:
        # Connection-backed tools open a fresh MCP session when invoked. Returning
        # tools loaded from a temporary ClientSession would leave them bound to a
        # closed stream as soon as this function returned.
        tools = await _client.get_tools(server_name=server)
        _breakers[server].record_success()
        return tools
    except Exception:  # noqa: BLE001 - discovery failures degrade one capability
        _breakers[server].record_failure()
        logger.warning("MCP tool discovery failed for %s", server)
        return []


def _health_url(mcp_url: str) -> str:
    base_url = mcp_url.rstrip("/")
    if base_url.endswith("/mcp"):
        base_url = base_url[:-4]
    return f"{base_url}/health"


async def _probe_server(
    _server: ServerName,
    mcp_url: str,
    client: httpx.AsyncClient,
) -> bool:
    try:
        response = await client.get(_health_url(mcp_url))
        if response.status_code >= 400:
            return False
        payload = response.json()
        return isinstance(payload, dict) and payload.get("status") == "ok"
    except (httpx.HTTPError, ValueError):
        return False


async def get_server_statuses() -> dict[ServerName, ServerStatus]:
    """Probe each MCP process without exposing internal service URLs."""
    servers = list(MCP_SERVER_URLS)
    async with httpx.AsyncClient(timeout=HEALTH_TIMEOUT, trust_env=False) as client:
        probes = await asyncio.gather(
            *(
                _probe_server(server, MCP_SERVER_URLS[server], client)
                for server in servers
            ),
            return_exceptions=True,
        )
    return {
        server: cast(
            ServerStatus,
            "available" if result is True else "unavailable",
        )
        for server, result in zip(servers, probes, strict=True)
    }
