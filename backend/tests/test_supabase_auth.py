from __future__ import annotations

import httpx
import pytest

from core.supabase_auth import ExternalAuthError, verify_supabase_google_token


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_verifies_google_identity_without_exposing_token(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "publishable-key")
    captured_authorization = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_authorization
        captured_authorization = request.headers["authorization"]
        return httpx.Response(
            200,
            json={
                "id": "subject-1",
                "email": "maya@example.com",
                "email_confirmed_at": "2026-07-17T10:00:00Z",
                "app_metadata": {"provider": "google", "providers": ["google"]},
                "user_metadata": {"full_name": "Maya Chen"},
            },
        )

    async with _client(handler) as client:
        identity = await verify_supabase_google_token(
            "private-access-token", client=client
        )

    assert captured_authorization == "Bearer private-access-token"
    assert identity.subject == "subject-1"
    assert identity.email == "maya@example.com"
    assert identity.name == "Maya Chen"


@pytest.mark.asyncio
async def test_rejects_non_google_or_unverified_identity(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "publishable-key")

    async with _client(
        lambda _request: httpx.Response(
            200,
            json={
                "id": "subject-2",
                "email": "maya@example.com",
                "app_metadata": {"provider": "email"},
            },
        )
    ) as client:
        with pytest.raises(ExternalAuthError, match="not a Google identity"):
            await verify_supabase_google_token("private-access-token", client=client)


@pytest.mark.asyncio
async def test_reports_missing_configuration_as_unavailable(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)

    with pytest.raises(ExternalAuthError) as exc_info:
        await verify_supabase_google_token("private-access-token")

    assert exc_info.value.status_code == 503
