from __future__ import annotations

from fastapi.testclient import TestClient

import main
from core import accounts
from core import security


def _client(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("TRIPWEAVER_DB_PATH", str(tmp_path / "accounts.sqlite3"))
    monkeypatch.setattr(security, "VALID_API_KEYS", {"test-key"})
    security._hits.clear()
    return TestClient(main.app)


def _register(client: TestClient, email: str = "traveller@example.com") -> dict:
    response = client.post(
        "/auth/register",
        headers={"X-API-Key": "test-key"},
        json={"email": email, "password": "correct horse", "name": "Traveller"},
    )
    assert response.status_code == 200
    return response.json()


def test_register_login_me_and_logout(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)

    registered = _register(client)
    assert registered["user"]["email"] == "traveller@example.com"
    assert registered["user"]["name"] == "Traveller"
    assert registered["token"]

    duplicate = client.post(
        "/auth/register",
        headers={"X-API-Key": "test-key"},
        json={"email": "traveller@example.com", "password": "correct horse"},
    )
    assert duplicate.status_code == 400

    login = client.post(
        "/auth/login",
        headers={"X-API-Key": "test-key"},
        json={"email": "traveller@example.com", "password": "correct horse"},
    )
    assert login.status_code == 200
    token = login.json()["token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "traveller@example.com"

    logout = client.post(
        "/auth/logout",
        headers={"X-API-Key": "test-key", "Authorization": f"Bearer {token}"},
    )
    assert logout.status_code == 200
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_conversations_are_private_to_the_authenticated_user(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    first = _register(client, "first@example.com")
    second = _register(client, "second@example.com")

    conversation = {
        "id": "trip-1",
        "title": "Tokyo plan",
        "sessionId": "abc123",
        "createdAt": "2026-07-14T10:00:00.000Z",
        "updatedAt": "2026-07-14T10:01:00.000Z",
        "tripContext": {
            "destination": "Tokyo",
            "dates": None,
            "travelers": None,
            "budget": None,
            "preferences": [],
        },
        "messages": [
            {
                "id": "m1",
                "role": "user",
                "content": "Plan Tokyo",
                "createdAt": "2026-07-14T10:00:00.000Z",
            }
        ],
    }

    saved = client.put(
        "/conversations/trip-1",
        headers={"Authorization": f"Bearer {first['token']}"},
        json={"conversation": conversation},
    )
    assert saved.status_code == 200

    first_history = client.get(
        "/conversations", headers={"Authorization": f"Bearer {first['token']}"}
    )
    assert first_history.status_code == 200
    assert first_history.json()["conversations"][0]["title"] == "Tokyo plan"

    second_history = client.get(
        "/conversations", headers={"Authorization": f"Bearer {second['token']}"}
    )
    assert second_history.status_code == 200
    assert second_history.json()["conversations"] == []

    second_trip = {
        **conversation,
        "id": "trip-2",
        "title": "Paris plan",
        "updatedAt": "2026-07-14T10:02:00.000Z",
    }
    assert (
        client.put(
            "/conversations/trip-2",
            headers={"Authorization": f"Bearer {first['token']}"},
            json={"conversation": second_trip},
        ).status_code
        == 200
    )

    deleted = client.delete(
        "/conversations/trip-1",
        headers={"Authorization": f"Bearer {first['token']}"},
    )
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True, "deleted": True}
    assert [
        item["id"]
        for item in client.get(
            "/conversations",
            headers={"Authorization": f"Bearer {first['token']}"},
        ).json()["conversations"]
    ] == ["trip-2"]
    assert (
        client.delete(
            "/conversations/trip-2",
            headers={"Authorization": f"Bearer {second['token']}"},
        ).json()["deleted"]
        is False
    )

    cleared = client.delete(
        "/conversations", headers={"Authorization": f"Bearer {first['token']}"}
    )
    assert cleared.status_code == 200
    assert (
        client.get("/conversations", headers={"Authorization": f"Bearer {first['token']}"})
        .json()["conversations"]
        == []
    )


def test_conversation_routes_require_account_session(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)

    assert client.get("/conversations").status_code == 401
    assert (
        client.put(
            "/conversations/trip-1",
            json={"conversation": {"id": "trip-1", "title": "Trip"}},
        ).status_code
        == 401
    )
    assert client.delete("/conversations/trip-1").status_code == 401


def test_plans_are_private_and_deletion_unassigns_conversations(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    first = _register(client, "planner@example.com")
    second = _register(client, "other@example.com")
    first_headers = {"Authorization": f"Bearer {first['token']}"}
    second_headers = {"Authorization": f"Bearer {second['token']}"}
    plan = {
        "id": "japan-plan",
        "name": "Japan 2027",
        "createdAt": "2026-07-16T08:00:00.000Z",
        "updatedAt": "2026-07-16T08:00:00.000Z",
    }

    saved = client.put("/plans/japan-plan", headers=first_headers, json={"plan": plan})
    assert saved.status_code == 200
    assert saved.json()["plan"]["name"] == "Japan 2027"
    assert client.get("/plans", headers=first_headers).json()["plans"] == [plan]
    assert client.get("/plans", headers=second_headers).json()["plans"] == []

    conversation = {
        "id": "tokyo-chat",
        "title": "Tokyo ideas",
        "planId": "japan-plan",
        "createdAt": "2026-07-16T08:01:00.000Z",
        "updatedAt": "2026-07-16T08:01:00.000Z",
        "messages": [],
        "tripContext": {},
    }
    assert client.put(
        "/conversations/tokyo-chat",
        headers=first_headers,
        json={"conversation": conversation},
    ).status_code == 200

    assert client.delete("/plans/japan-plan", headers=second_headers).json()["deleted"] is False
    assert client.delete("/plans/japan-plan", headers=first_headers).json() == {
        "ok": True,
        "deleted": True,
    }
    assert client.get("/plans", headers=first_headers).json()["plans"] == []
    stored_chat = client.get("/conversations", headers=first_headers).json()["conversations"][0]
    assert "planId" not in stored_chat


def test_plan_routes_require_account_session(monkeypatch, tmp_path):
    assert _client(monkeypatch, tmp_path).get("/plans").status_code == 401


def test_database_url_selects_postgres_sql(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.example/postgres")

    assert accounts._uses_postgres()
    assert accounts._sql("SELECT * FROM users WHERE email = ?") == (
        "SELECT * FROM users WHERE email = %s"
    )


def test_sqlite_remains_default_without_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert not accounts._uses_postgres()
    assert accounts._sql("SELECT * FROM users WHERE email = ?") == (
        "SELECT * FROM users WHERE email = ?"
    )
