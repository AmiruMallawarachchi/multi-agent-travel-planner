"""
backend/tests/test_security.py
Unit tests for core/security.py - the auth, rate-limiting, input-validation
and session-id primitives that sit in front of every billable endpoint.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from core import security


class TestMessageSanitization:
    def test_strips_control_characters(self):
        assert security.sanitize_user_message("hello\x00\x07world") == "helloworld"

    def test_trims_whitespace(self):
        assert security.sanitize_user_message("  hi there  ") == "hi there"

    def test_rejects_empty_message(self):
        with pytest.raises(ValueError):
            security.sanitize_user_message("   ")

    def test_rejects_message_over_max_length(self, monkeypatch):
        monkeypatch.setattr(security, "MAX_MESSAGE_LENGTH", 10)
        with pytest.raises(ValueError):
            security.sanitize_user_message("this message is definitely too long")

    def test_accepts_message_within_limit(self, monkeypatch):
        monkeypatch.setattr(security, "MAX_MESSAGE_LENGTH", 10)
        assert security.sanitize_user_message("short") == "short"


class TestSessionIds:
    def test_new_session_id_round_trips_validation(self):
        sid = security.new_session_id()
        assert security.validate_session_id(sid) == sid

    @pytest.mark.parametrize(
        "bad_id",
        ["", "not-a-uuid", "'; DROP TABLE sessions; --", "a" * 31, "a" * 33, "G" * 32],
    )
    def test_rejects_anything_that_is_not_a_bare_uuid4_hex(self, bad_id):
        with pytest.raises(ValueError):
            security.validate_session_id(bad_id)


class TestRateLimiting:
    def test_allows_requests_under_the_limit(self, monkeypatch):
        monkeypatch.setattr(security, "RATE_LIMIT_REQUESTS", 3)
        monkeypatch.setattr(security, "RATE_LIMIT_WINDOW_SECONDS", 60)
        identity = "test-under-limit"
        for _ in range(3):
            security.check_rate_limit(identity)  # should not raise

    def test_blocks_requests_over_the_limit(self, monkeypatch):
        monkeypatch.setattr(security, "RATE_LIMIT_REQUESTS", 2)
        monkeypatch.setattr(security, "RATE_LIMIT_WINDOW_SECONDS", 60)
        identity = "test-over-limit"
        security.check_rate_limit(identity)
        security.check_rate_limit(identity)
        with pytest.raises(HTTPException) as exc_info:
            security.check_rate_limit(identity)
        assert exc_info.value.status_code == 429

    def test_different_identities_have_independent_limits(self, monkeypatch):
        monkeypatch.setattr(security, "RATE_LIMIT_REQUESTS", 1)
        monkeypatch.setattr(security, "RATE_LIMIT_WINDOW_SECONDS", 60)
        security.check_rate_limit("identity-a")
        security.check_rate_limit("identity-b")  # independent bucket, should not raise


class TestApiKeyAuth:
    @pytest.mark.asyncio
    async def test_allows_anonymous_when_no_keys_configured(self, monkeypatch):
        monkeypatch.setattr(security, "VALID_API_KEYS", set())
        result = await security.require_api_key(x_api_key=None)
        assert result == "anonymous"

    @pytest.mark.asyncio
    async def test_rejects_missing_key_when_keys_are_configured(self, monkeypatch):
        monkeypatch.setattr(security, "VALID_API_KEYS", {"good-key"})
        with pytest.raises(HTTPException) as exc_info:
            await security.require_api_key(x_api_key=None)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_rejects_wrong_key(self, monkeypatch):
        monkeypatch.setattr(security, "VALID_API_KEYS", {"good-key"})
        with pytest.raises(HTTPException):
            await security.require_api_key(x_api_key="wrong-key")

    @pytest.mark.asyncio
    async def test_accepts_correct_key(self, monkeypatch):
        monkeypatch.setattr(security, "VALID_API_KEYS", {"good-key"})
        result = await security.require_api_key(x_api_key="good-key")
        assert result == "good-key"
