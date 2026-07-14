from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agents import mcp_client


EXPECTED_SERVERS = {
    "hotel-mcp",
    "flight-mcp",
    "itinerary-mcp",
    "weather-mcp",
    "currency-mcp",
    "location-mcp",
}


def test_registry_contains_every_tripweaver_mcp_service():
    assert set(mcp_client.MCP_SERVER_URLS) == EXPECTED_SERVERS
    assert set(mcp_client._breakers) == EXPECTED_SERVERS


@pytest.mark.asyncio
async def test_tools_are_connection_backed_and_scoped_to_one_server(monkeypatch):
    tool = SimpleNamespace(name="get_weather_forecast")
    get_tools = AsyncMock(return_value=[tool])
    monkeypatch.setattr(
        mcp_client,
        "_client",
        SimpleNamespace(get_tools=get_tools),
    )
    mcp_client._breakers["weather-mcp"].record_success()

    tools = await mcp_client.get_tools_for("weather-mcp")

    assert tools == [tool]
    get_tools.assert_awaited_once_with(server_name="weather-mcp")


@pytest.mark.asyncio
async def test_health_statuses_are_normalized_without_exposing_urls(monkeypatch):
    class SharedClient:
        instances = 0

        def __init__(self, *, timeout, trust_env):
            SharedClient.instances += 1
            assert timeout is mcp_client.HEALTH_TIMEOUT
            assert trust_env is False

        async def __aenter__(self):
            return self

        async def __aexit__(self, _exc_type, _exc, _traceback):
            return None

    clients = []

    async def probe(server, _url, client):
        clients.append(client)
        return server not in {"weather-mcp", "location-mcp"}

    monkeypatch.setattr(mcp_client.httpx, "AsyncClient", SharedClient)
    monkeypatch.setattr(mcp_client, "_probe_server", AsyncMock(side_effect=probe))

    statuses = await mcp_client.get_server_statuses()

    assert SharedClient.instances == 1
    assert len(clients) == len(EXPECTED_SERVERS)
    assert all(client is clients[0] for client in clients)
    assert statuses["hotel-mcp"] == "available"
    assert statuses["weather-mcp"] == "unavailable"
    assert statuses["location-mcp"] == "unavailable"
    assert all("http" not in value for value in statuses.values())
