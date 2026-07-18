"""
core/security.py
Security & guardrail primitives for the FastAPI layer. See SECURITY.md for
the full write-up (what this defends against and what it deliberately does
not, e.g. this is single-instance rate limiting, not a WAF).

  1. API-key auth        - the chat endpoint is billable (OpenAI + SerpApi);
                            it must not be open to the whole internet.
  2. Rate limiting        - a sliding window per API key / IP, so one client
                            can't exhaust your OpenAI budget or SerpApi quota.
  3. Input validation     - length caps + control-character stripping on
                            every user message before it reaches the graph.
  4. Session-id hygiene   - unguessable ids issued by us; anything else is
                            rejected before it's ever used as a LangGraph
                            thread_id, so one traveller can't read another's
                            conversation by guessing a session id.
"""
from __future__ import annotations

import os
import re
import time
import uuid
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request, status

# ---------------------------------------------------------------------------
# API-key auth
# ---------------------------------------------------------------------------
# Comma-separated allowlist in env, e.g. TRIPWEAVER_API_KEYS="key-for-web,key-for-mobile".
# Empty by default so local dev / docker compose "just works" out of the box;
# a real deployment MUST set this (README "Deployment" section flags it).
_RAW_KEYS = os.getenv("TRIPWEAVER_API_KEYS", "")
VALID_API_KEYS = {k.strip() for k in _RAW_KEYS.split(",") if k.strip()}


async def require_api_key(x_api_key: str | None = Header(default=None)) -> str:
    if not VALID_API_KEYS:
        # No keys configured - local/dev mode only. Logged loudly at
        # startup in main.py so it's never silently left open in prod.
        return "anonymous"
    if not x_api_key or x_api_key not in VALID_API_KEYS:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or invalid X-API-Key header")
    return x_api_key


# ---------------------------------------------------------------------------
# Rate limiting - in-memory sliding window. Good enough for a single-instance
# deployment (the Render demo runs one backend instance); swap the dict below
# for Redis if you scale horizontally.
# ---------------------------------------------------------------------------
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "20"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

_hits: dict[str, deque] = defaultdict(deque)


def client_identity(request: Request, api_key: str) -> str:
    if api_key != "anonymous":
        return f"key:{api_key}"
    return f"ip:{request.client.host if request.client else 'unknown'}"


def check_rate_limit(identity: str) -> None:
    now = time.monotonic()
    window = _hits[identity]
    while window and now - window[0] > RATE_LIMIT_WINDOW_SECONDS:
        window.popleft()
    if len(window) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Rate limit exceeded - max {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW_SECONDS}s. "
            "Please wait a moment before trying again.",
        )
    window.append(now)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
MAX_MESSAGE_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", "2000"))
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def sanitize_user_message(text: str) -> str:
    """Strip control characters and cap length. This is NOT a prompt-
    injection filter - that defense lives in agents/nodes.py and
    agents/prompts.py, because it has to operate on tool output too, not
    just the traveller's own text. This just stops abuse and garbage input
    before it reaches the graph at all."""
    text = _CONTROL_CHARS.sub("", text).strip()
    if not text:
        raise ValueError("Message is empty")
    if len(text) > MAX_MESSAGE_LENGTH:
        raise ValueError(f"Message exceeds {MAX_MESSAGE_LENGTH} characters")
    return text


# ---------------------------------------------------------------------------
# Session ids
# ---------------------------------------------------------------------------
_SESSION_ID_RE = re.compile(r"^[0-9a-f]{32}$")


def new_session_id() -> str:
    """UUID4 hex - unguessable, so a session id can't be enumerated."""
    return uuid.uuid4().hex


def validate_session_id(session_id: str) -> str:
    """Reject anything that doesn't look like an id we issued, before it's
    ever used as a LangGraph thread_id (which would resume - and expose -
    that thread's conversation) or written to logs."""
    if not _SESSION_ID_RE.fullmatch(session_id):
        raise ValueError("Invalid session id")
    return session_id
