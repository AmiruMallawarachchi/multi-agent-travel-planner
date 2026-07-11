"""
main.py
FastAPI backend fronting the LangGraph multi-agent workflow (SRS section 1.4).

Endpoints:
  GET  /health          - liveness check (unauthenticated, for Railway/uptime monitors)
  POST /session          - mint a fresh, unguessable session id
  POST /chat/stream      - SSE stream of routing/activity/token/done/error events

Security & guardrails applied here (see SECURITY.md for the full picture):
  - X-API-Key auth on every billable endpoint (core/security.require_api_key)
  - per-key/IP rate limiting (core/security.check_rate_limit)
  - input length/control-character sanitisation before anything reaches the graph
  - session ids are minted server-side and validated on every use
  - CORS locked to an explicit allowlist from env, not "*"
  - every exception is caught at the top of the stream and turned into a
    user-friendly SSE "error" event - the process never crashes on a bad
    turn (SRS section 5 / 7)
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

load_dotenv()

from agents.graph import graph
from core.security import (
    VALID_API_KEYS,
    check_rate_limit,
    client_identity,
    new_session_id,
    require_api_key,
    sanitize_user_message,
    validate_session_id,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("tripweaver")

if not VALID_API_KEYS:
    logger.warning(
        "TRIPWEAVER_API_KEYS is not set - /chat/stream is running WITHOUT auth. "
        "This is fine for local dev only; set it before deploying (see README)."
    )

app = FastAPI(title="TripWeaver API", version="1.0.0")

_allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins or ["http://localhost:7860"],  # Gradio's local default port
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "X-API-Key"],
)

# Node name -> user-facing activity label, matching SRS section 6 exactly so
# the frontend's activity indicator is a direct rendering of this map.
NODE_ACTIVITY = {
    "classify_intent": "ROUTING",
    "general_qa": "RESPONDING",
    "hotel": "SEARCHING",
    "flight": "SEARCHING",
    "clarify": "CLARIFYING",
}


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "tripweaver-backend"}


@app.post("/session")
async def create_session(request: Request, api_key: str = Depends(require_api_key)) -> dict:
    # Rate-limited too: it's cheap per-call, but uncapped it's still a free
    # enumeration/DoS surface, and it shares the same identity bucket as
    # /chat/stream so the two endpoints can't be used to double a client's
    # effective budget.
    check_rate_limit(client_identity(request, api_key))
    return {"session_id": new_session_id()}


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


@app.post("/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    request: Request,
    api_key: str = Depends(require_api_key),
):
    identity = client_identity(request, api_key)
    check_rate_limit(identity)

    request_id = uuid.uuid4().hex[:8]
    try:
        message = sanitize_user_message(payload.message)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    session_id = payload.session_id or new_session_id()
    try:
        session_id = validate_session_id(session_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    config = {"configurable": {"thread_id": session_id}}
    inputs = {"messages": [{"role": "user", "content": message}], "session_id": session_id}

    logger.info("request_id=%s session=%s identity=%s chars=%d", request_id, session_id, identity, len(message))
    started = time.monotonic()

    async def event_generator():
        yield _sse({"type": "session", "session_id": session_id})
        try:
            async for event in graph.astream_events(inputs, config=config, version="v2"):
                kind = event["event"]
                name = event.get("name", "")

                if kind == "on_chain_start" and name in NODE_ACTIVITY:
                    yield _sse({"type": "status", "state": NODE_ACTIVITY[name], "node": name})

                elif kind == "on_tool_start":
                    yield _sse({"type": "tool", "status": "INVOKED", "tool": name})

                elif kind == "on_tool_end":
                    yield _sse({"type": "tool", "status": "SUCCEEDED", "tool": name})

                elif kind == "on_tool_error":
                    yield _sse({"type": "tool", "status": "FAILED", "tool": name})

                elif kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    content = getattr(chunk, "content", "")
                    if content:
                        yield _sse({"type": "token", "content": content})

            elapsed_ms = int((time.monotonic() - started) * 1000)
            logger.info("request_id=%s session=%s completed in %dms", request_id, session_id, elapsed_ms)
            yield _sse({"type": "done"})

        except Exception:  # noqa: BLE001 - SRS 5/7: never crash the conversation
            logger.exception("request_id=%s session=%s chat_stream failed", request_id, session_id)
            yield _sse(
                {
                    "type": "error",
                    "message": "Something went wrong on our side. The rest of TripWeaver is "
                    "still up - please try again.",
                }
            )

    return StreamingResponse(event_generator(), media_type="text/event-stream")
