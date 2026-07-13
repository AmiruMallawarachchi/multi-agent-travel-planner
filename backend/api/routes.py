"""HTTP route handlers for TripWeaver."""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from agents.graph import graph
from api.schemas import ChatRequest, HealthResponse, SessionEvent, SessionResponse
from api.sse import done_event, encode_sse, stream_events_from_graph_event, user_safe_error
from core.security import (
    check_rate_limit,
    client_identity,
    new_session_id,
    require_api_key,
    sanitize_user_message,
    validate_session_id,
)

logger = logging.getLogger("tripweaver")
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="tripweaver-backend")


@router.post("/session", response_model=SessionResponse)
async def create_session(request: Request, api_key: str = Depends(require_api_key)) -> SessionResponse:
    check_rate_limit(client_identity(request, api_key))
    return SessionResponse(session_id=new_session_id())


@router.post("/chat/stream")
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
        yield encode_sse(SessionEvent(session_id=session_id))
        try:
            async for event in graph.astream_events(inputs, config=config, version="v2"):
                for stream_event in stream_events_from_graph_event(event):
                    yield encode_sse(stream_event)

            elapsed_ms = int((time.monotonic() - started) * 1000)
            logger.info("request_id=%s session=%s completed in %dms", request_id, session_id, elapsed_ms)
            yield encode_sse(done_event())

        except Exception:  # noqa: BLE001 - conversation failures become user-safe SSE events
            logger.exception("request_id=%s session=%s chat_stream failed", request_id, session_id)
            yield encode_sse(user_safe_error())
            yield encode_sse(done_event())

    return StreamingResponse(event_generator(), media_type="text/event-stream")
