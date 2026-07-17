"""Validation for Supabase-issued social-login access tokens."""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx


class ExternalAuthError(ValueError):
    def __init__(self, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class ExternalIdentity:
    provider: str
    subject: str
    email: str
    name: str | None


async def verify_supabase_google_token(
    access_token: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> ExternalIdentity:
    token = access_token.strip()
    if not token or len(token) > 8192:
        raise ExternalAuthError("Invalid Google sign-in token")

    supabase_url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    publishable_key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
    if not supabase_url or not publishable_key:
        raise ExternalAuthError("Google sign-in is not configured", status_code=503)

    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=3.0),
            follow_redirects=False,
        )

    try:
        response = await client.get(
            f"{supabase_url}/auth/v1/user",
            headers={
                "apikey": publishable_key,
                "Authorization": f"Bearer {token}",
            },
        )
    except httpx.HTTPError as exc:
        raise ExternalAuthError(
            "Google sign-in verification is temporarily unavailable", status_code=503
        ) from exc
    finally:
        if owns_client:
            await client.aclose()

    if response.status_code != 200:
        raise ExternalAuthError("Google sign-in could not be verified")

    try:
        payload = response.json()
    except ValueError as exc:
        raise ExternalAuthError("Google sign-in returned an invalid response") from exc

    app_metadata = payload.get("app_metadata") or {}
    providers = app_metadata.get("providers") or []
    provider = app_metadata.get("provider")
    if provider != "google" and "google" not in providers:
        raise ExternalAuthError("The supplied account is not a Google identity")

    subject = str(payload.get("id") or "").strip()
    email = str(payload.get("email") or "").strip()
    if not subject or not email or not payload.get("email_confirmed_at"):
        raise ExternalAuthError("Google account email is not verified")

    user_metadata = payload.get("user_metadata") or {}
    name = user_metadata.get("full_name") or user_metadata.get("name")
    return ExternalIdentity(
        provider="google",
        subject=subject,
        email=email,
        name=str(name).strip() if name else None,
    )
