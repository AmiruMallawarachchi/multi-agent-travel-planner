"""
Endpoint-level tests for the FastAPI security and SSE bridge.

These stay offline: the LangGraph object is replaced with a tiny async fake so
we can verify auth, sessions, CORS, tool-status events, and graceful failures
without OpenAI or MCP servers.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from api import routes
import main
from core import security


class FakeGraph:
    def __init__(self, events=None, exc: Exception | None = None):
        self.events = events or []
        self.exc = exc
        self.calls = []

    async def astream_events(self, inputs, config, version):
        self.calls.append({"inputs": inputs, "config": config, "version": version})
        if self.exc:
            raise self.exc
        for event in self.events:
            yield event


def _events(body: str) -> list[dict]:
    parsed = []
    for part in body.strip().split("\n\n"):
        if part.startswith("data: "):
            parsed.append(json.loads(part[6:]))
    return parsed


def _client(
    monkeypatch, *, keys: set[str] | None = None, rate_limit: int = 20
) -> TestClient:
    monkeypatch.setattr(
        security, "VALID_API_KEYS", keys if keys is not None else {"test-key"}
    )
    security._hits.clear()
    monkeypatch.setattr(security, "RATE_LIMIT_REQUESTS", rate_limit)
    monkeypatch.setattr(security, "RATE_LIMIT_WINDOW_SECONDS", 60)
    return TestClient(main.app)


class TestApiSecurity:
    def test_health_is_unauthenticated(self, monkeypatch):
        async def statuses():
            return {
                "hotel-mcp": "available",
                "flight-mcp": "available",
                "itinerary-mcp": "available",
                "weather-mcp": "unavailable",
                "currency-mcp": "available",
                "location-mcp": "unavailable",
            }

        monkeypatch.setattr(routes, "get_server_statuses", statuses)
        client = _client(monkeypatch)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "service": "tripweaver-backend",
            "mcp_servers": {
                "hotel-mcp": "available",
                "flight-mcp": "available",
                "itinerary-mcp": "available",
                "weather-mcp": "unavailable",
                "currency-mcp": "available",
                "location-mcp": "unavailable",
            },
        }

    def test_session_requires_api_key_when_configured(self, monkeypatch):
        client = _client(monkeypatch)
        assert client.post("/session").status_code == 401
        assert (
            client.post("/session", headers={"X-API-Key": "wrong"}).status_code == 401
        )

        response = client.post("/session", headers={"X-API-Key": "test-key"})
        assert response.status_code == 200
        assert security.validate_session_id(response.json()["session_id"])

    def test_session_and_chat_share_rate_limit_bucket(self, monkeypatch):
        fake_graph = FakeGraph()
        monkeypatch.setattr(routes, "graph", fake_graph)
        client = _client(monkeypatch, rate_limit=1)

        assert (
            client.post("/session", headers={"X-API-Key": "test-key"}).status_code
            == 200
        )
        response = client.post(
            "/chat/stream",
            headers={"X-API-Key": "test-key"},
            json={"message": "hello"},
        )
        assert response.status_code == 429

    def test_invalid_session_id_is_rejected_before_graph_runs(self, monkeypatch):
        fake_graph = FakeGraph()
        monkeypatch.setattr(routes, "graph", fake_graph)
        client = _client(monkeypatch)

        response = client.post(
            "/chat/stream",
            headers={"X-API-Key": "test-key"},
            json={"message": "hello", "session_id": "'; DROP TABLE sessions; --"},
        )

        assert response.status_code == 422
        assert fake_graph.calls == []

    def test_disallowed_cors_origin_is_not_echoed(self, monkeypatch):
        client = _client(monkeypatch)
        response = client.options(
            "/chat/stream",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-API-Key, Content-Type",
            },
        )
        assert "access-control-allow-origin" not in response.headers


class TestSseBridge:
    def test_stream_emits_session_status_tool_token_and_done(self, monkeypatch):
        fake_graph = FakeGraph(
            [
                {"event": "on_chain_start", "name": "classify_intent"},
                {"event": "on_tool_start", "name": "search_hotels"},
                {"event": "on_tool_end", "name": "search_hotels"},
                {
                    "event": "on_chat_model_stream",
                    "data": {"chunk": type("Chunk", (), {"content": "hello"})()},
                },
            ]
        )
        monkeypatch.setattr(routes, "graph", fake_graph)
        client = _client(monkeypatch)

        response = client.post(
            "/chat/stream",
            headers={"X-API-Key": "test-key"},
            json={"message": "find hotels"},
        )

        assert response.status_code == 200
        events = _events(response.text)
        assert events[0]["type"] == "session"
        assert {
            "type": "status",
            "state": "ROUTING",
            "node": "classify_intent",
        } in events
        assert {"type": "tool", "status": "INVOKED", "tool": "search_hotels"} in events
        assert {
            "type": "tool",
            "status": "SUCCEEDED",
            "tool": "search_hotels",
        } in events
        assert {"type": "token", "content": "hello"} in events
        assert events[-1] == {"type": "done"}

    def test_stream_emits_structured_itinerary_result(self, monkeypatch):
        fake_graph = FakeGraph(
            [
                {
                    "event": "on_tool_end",
                    "name": "create_itinerary",
                    "data": {
                        "output": {
                            "ok": True,
                            "itinerary": {
                                "destination": "Tokyo",
                                "days": [{"date": "2026-12-10", "items": []}],
                            },
                        }
                    },
                }
            ]
        )
        monkeypatch.setattr(routes, "graph", fake_graph)
        client = _client(monkeypatch)

        response = client.post(
            "/chat/stream",
            headers={"X-API-Key": "test-key"},
            json={"message": "plan Tokyo"},
        )

        events = _events(response.text)
        result = next(event for event in events if event["type"] == "result")
        assert result["result_type"] == "itinerary"
        assert result["tool"] == "create_itinerary"
        assert result["data"]["destination"] == "Tokyo"

    def test_stream_normalizes_frontend_friendly_events(self, monkeypatch):
        fake_graph = FakeGraph(
            [
                {"event": "on_tool_start", "name": ""},
                {
                    "event": "on_chat_model_stream",
                    "data": {
                        "chunk": type(
                            "Chunk", (), {"content": [{"text": "hel"}, "lo"]}
                        )()
                    },
                },
                {"event": "unknown_event"},
            ]
        )
        monkeypatch.setattr(routes, "graph", fake_graph)
        client = _client(monkeypatch)

        response = client.post(
            "/chat/stream",
            headers={"X-API-Key": "test-key"},
            json={"message": "find hotels"},
        )

        assert response.status_code == 200
        events = _events(response.text)
        assert {"type": "tool", "status": "INVOKED", "tool": "tool"} in events
        assert {"type": "token", "content": "hello"} in events
        assert events[-1] == {"type": "done"}

    def test_stream_turns_graph_exception_into_error_event(self, monkeypatch):
        fake_graph = FakeGraph(exc=RuntimeError("boom"))
        monkeypatch.setattr(routes, "graph", fake_graph)
        client = _client(monkeypatch)

        response = client.post(
            "/chat/stream",
            headers={"X-API-Key": "test-key"},
            json={"message": "find flights"},
        )

        assert response.status_code == 200
        events = _events(response.text)
        assert events[0]["type"] == "session"
        assert events[1]["type"] == "error"
        assert "Something went wrong" in events[1]["message"]
        assert events[-1] == {"type": "done"}
