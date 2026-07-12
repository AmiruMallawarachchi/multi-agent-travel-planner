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


def _chunk_text(content) -> str:
    if not content:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
        return "".join(parts)
    return str(content)


def _result_dict(output) -> dict | None:
    """Recover a structured MCP result from common LangChain output shapes."""
    if isinstance(output, dict):
        return output
    if isinstance(output, str):
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    content = getattr(output, "content", None)
    if isinstance(content, str):
        return _result_dict(content)
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                candidate = item.get("text", item)
                parsed = _result_dict(candidate)
                if parsed:
                    return parsed
            else:
                parsed = _result_dict(getattr(item, "text", None))
                if parsed:
                    return parsed
    return None


def _hotel_card(raw: dict) -> dict:
    hotel = raw.get("hotel") if isinstance(raw.get("hotel"), dict) else raw
    offers = raw.get("offers") if isinstance(raw.get("offers"), list) else []
    offer = offers[0] if offers and isinstance(offers[0], dict) else {}
    price = offer.get("price") if isinstance(offer.get("price"), dict) else {}
    room = offer.get("room") if isinstance(offer.get("room"), dict) else {}
    estimate = room.get("typeEstimated") if isinstance(room.get("typeEstimated"), dict) else {}
    description = room.get("description") if isinstance(room.get("description"), dict) else {}
    address = hotel.get("address") if isinstance(hotel.get("address"), dict) else {}
    return {
        "id": offer.get("id") or hotel.get("hotelId") or raw.get("id"),
        "hotel_id": hotel.get("hotelId") or raw.get("hotelId"),
        "name": hotel.get("name") or raw.get("name") or "Hotel option",
        "city_code": hotel.get("cityCode") or raw.get("iataCode") or raw.get("cityCode"),
        "address": ", ".join(address.get("lines", [])) if isinstance(address.get("lines"), list) else None,
        "rating": hotel.get("rating"),
        "check_in": offer.get("checkInDate"),
        "check_out": offer.get("checkOutDate"),
        "room": estimate.get("category") or description.get("text"),
        "beds": estimate.get("beds"),
        "bed_type": estimate.get("bedType"),
        "price": price.get("total"),
        "currency": price.get("currency"),
        "available": raw.get("available", True),
    }


def _flight_card(raw: dict) -> dict:
    itineraries = raw.get("itineraries") if isinstance(raw.get("itineraries"), list) else []
    itinerary = itineraries[0] if itineraries and isinstance(itineraries[0], dict) else {}
    segments = itinerary.get("segments") if isinstance(itinerary.get("segments"), list) else []
    first = segments[0] if segments and isinstance(segments[0], dict) else {}
    last = segments[-1] if segments and isinstance(segments[-1], dict) else {}
    departure = first.get("departure") if isinstance(first.get("departure"), dict) else {}
    arrival = last.get("arrival") if isinstance(last.get("arrival"), dict) else {}
    price = raw.get("price") if isinstance(raw.get("price"), dict) else {}
    aircraft = first.get("aircraft") if isinstance(first.get("aircraft"), dict) else {}
    return {
        "id": raw.get("id"),
        "origin": departure.get("iataCode"),
        "destination": arrival.get("iataCode"),
        "departure_at": departure.get("at"),
        "arrival_at": arrival.get("at"),
        "duration": itinerary.get("duration"),
        "stops": max(0, len(segments) - 1),
        "carrier": first.get("carrierCode") or (raw.get("validatingAirlineCodes") or [None])[0],
        "flight_number": first.get("number"),
        "aircraft": aircraft.get("code"),
        "price": price.get("grandTotal") or price.get("total"),
        "currency": price.get("currency"),
        "seats": raw.get("numberOfBookableSeats"),
    }


def _structured_result_event(tool_name: str, output) -> dict | None:
    result = _result_dict(output)
    if not result or result.get("ok") is not True:
        return None

    if tool_name in {"list_hotels", "search_hotels"}:
        source = result.get("offers") if tool_name == "search_hotels" else result.get("hotels")
        items = source if isinstance(source, list) else []
        return {
            "type": "result",
            "category": "hotel",
            "tool": tool_name,
            "items": [_hotel_card(item) for item in items[:5] if isinstance(item, dict)],
        }

    if tool_name in {"list_flights", "search_flights"}:
        source = result.get("offers") if tool_name == "search_flights" else result.get("flights")
        items = source if isinstance(source, list) else []
        return {
            "type": "result",
            "category": "flight",
            "tool": tool_name,
            "items": [_flight_card(item) for item in items[:5] if isinstance(item, dict)],
        }

    if tool_name in {"book_hotel", "book_flight"}:
        confirmation = result.get("confirmation")
        if not isinstance(confirmation, dict) or confirmation.get("simulated") is not True:
            return None
        return {
            "type": "result",
            "category": "booking",
            "tool": tool_name,
            "confirmation": {
                "type": "hotel" if tool_name == "book_hotel" else "flight",
                "confirmation_number": confirmation.get("confirmation_number"),
                "offer_id": confirmation.get("offer_id"),
                "traveller_name": confirmation.get("traveller_name") or confirmation.get("guest_name"),
                "status": confirmation.get("status"),
                "booked_at": confirmation.get("booked_at"),
                "simulated": True,
            },
        }
    return None


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
                kind = event.get("event", "")
                name = event.get("name", "")

                if kind == "on_chain_start" and name in NODE_ACTIVITY:
                    yield _sse({"type": "status", "state": NODE_ACTIVITY[name], "node": name})

                elif kind == "on_tool_start":
                    yield _sse({"type": "tool", "status": "INVOKED", "tool": name or "tool"})

                elif kind == "on_tool_end":
                    yield _sse({"type": "tool", "status": "SUCCEEDED", "tool": name or "tool"})
                    structured = _structured_result_event(
                        name, event.get("data", {}).get("output")
                    )
                    if structured:
                        yield _sse(structured)

                elif kind == "on_tool_error":
                    yield _sse({"type": "tool", "status": "FAILED", "tool": name or "tool"})

                elif kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    content = _chunk_text(getattr(chunk, "content", ""))
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
            yield _sse({"type": "done"})

    return StreamingResponse(event_generator(), media_type="text/event-stream")
