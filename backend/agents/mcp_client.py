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

import os
import time
from dataclasses import dataclass
from typing import Literal

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

ServerName = Literal["hotel-mcp", "flight-mcp"]

HOTEL_MCP_URL = os.getenv("HOTEL_MCP_URL", "http://localhost:8001/mcp")
FLIGHT_MCP_URL = os.getenv("FLIGHT_MCP_URL", "http://localhost:8002/mcp")

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


_breakers: dict[str, _Breaker] = {"hotel-mcp": _Breaker(), "flight-mcp": _Breaker()}

# One client, both servers. Adding a third MCP server later (SRS section 9
# stretch - "activities, local transport, weather") means adding one entry
# here and one new node/prompt pair - nothing else in the graph changes.
_client = MultiServerMCPClient(
    {
        "hotel-mcp": {"url": HOTEL_MCP_URL, "transport": "http"},
        "flight-mcp": {"url": FLIGHT_MCP_URL, "transport": "http"},
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
        async with _client.session(server) as session:
            tools = await load_mcp_tools(session)
        _breakers[server].record_success()
        return tools
    except Exception:
        _breakers[server].record_failure()
        return []
