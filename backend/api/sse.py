"""SSE encoding and LangGraph event normalization."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from agents.entity import ActivityState
from agents.tool_results import tool_result_dict
from api.schemas import (
    DoneEvent,
    ErrorEvent,
    QuickRepliesEvent,
    QuickReplyOption,
    ResultEvent,
    StatusEvent,
    StreamEvent,
    TokenEvent,
    ToolEvent,
)

NODE_ACTIVITY = {
    "classify_intent": ActivityState.ROUTING.value,
    "general_qa": ActivityState.RESPONDING.value,
    "hotel": ActivityState.SEARCHING.value,
    "flight": ActivityState.SEARCHING.value,
    "itinerary": ActivityState.SEARCHING.value,
    "weather": ActivityState.SEARCHING.value,
    "currency": ActivityState.SEARCHING.value,
    "location": ActivityState.SEARCHING.value,
    "clarify": ActivityState.CLARIFYING.value,
}
RESPONSE_NODES = frozenset(NODE_ACTIVITY) - {"classify_intent"}

STRUCTURED_TOOL_RESULTS = {
    "list_flights": ("flight", "flights"),
    "search_flights": ("flight", "offers"),
    "list_hotels": ("hotel", "hotels"),
    "search_hotels": ("hotel", "offers"),
    "create_itinerary": ("itinerary", "itinerary"),
    "get_current_weather": ("weather", "weather"),
    "get_weather_forecast": ("weather", "weather"),
    "convert_currency": ("currency", "result"),
    "get_exchange_rate": ("currency", "result"),
    "list_supported_currencies": ("currency", "result"),
    "resolve_location": ("location", "locations"),
    "search_places": ("location", "places"),
}


def encode_sse(event: StreamEvent) -> str:
    return f"data: {event.model_dump_json()}\n\n"


def encode_raw_sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event)}\n\n"


def chunk_text(content: Any) -> str:
    if not content:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
        return "".join(parts)
    return str(content)


def _tool_payload(event: dict[str, Any]) -> dict[str, Any] | None:
    raw_output = event.get("data", {}).get("output")
    if hasattr(raw_output, "content"):
        raw_output = raw_output.content
    return tool_result_dict(raw_output)


def _options(*values: tuple[str, str]) -> list[QuickReplyOption]:
    return [
        QuickReplyOption(id=f"choice-{index}", label=label, value=value)
        for index, (label, value) in enumerate(values, start=1)
    ]


def quick_replies_for_text(content: str) -> QuickRepliesEvent | None:
    normalized = " ".join(content.lower().split())
    if "?" not in normalized:
        return None

    if any(term in normalized for term in ("travel date", "check-in", "check in", "departure date", "when do you")):
        options = _options(
            ("This weekend", "This weekend"),
            ("Next month", "Next month"),
            ("In three months", "In about three months"),
            ("Dates are flexible", "My dates are flexible"),
        )
    elif any(term in normalized for term in ("how many travel", "how many guest", "how many adult")):
        options = _options(
            ("Solo", "1 traveller"),
            ("Two people", "2 travellers"),
            ("Family", "3 to 4 travellers"),
            ("Group", "5 or more travellers"),
        )
    elif any(term in normalized for term in ("interest", "kind of trip", "activities")):
        options = _options(
            ("Food and culture", "Food and culture"),
            ("Beach and relaxation", "Beaches and relaxation"),
            ("Adventure and nature", "Adventure and nature"),
            ("Shopping and nightlife", "Shopping and nightlife"),
        )
    elif "budget" in normalized:
        options = _options(
            ("Budget", "Keep the trip budget-friendly"),
            ("Mid-range", "Use a comfortable mid-range budget"),
            ("Premium", "Use a premium budget"),
            ("Not sure yet", "My budget is not decided yet"),
        )
    elif any(term in normalized for term in ("pace", "busy should", "packed")):
        options = _options(
            ("Relaxed", "Use a relaxed pace"),
            ("Balanced", "Use a balanced pace"),
            ("Packed", "Fit in as much as practical"),
            ("Decide for me", "Choose the best pace for this trip"),
        )
    elif any(term in normalized for term in ("one way", "round trip", "return flight")):
        options = _options(
            ("Round trip", "I need a round-trip flight"),
            ("One way", "I need a one-way flight"),
            ("Multi-city", "I need a multi-city flight"),
        )
    else:
        return None

    return QuickRepliesEvent(options=options)


def stream_events_from_graph_event(event: dict[str, Any]) -> Iterable[StreamEvent]:
    kind = event.get("event", "")
    name = event.get("name", "")

    if kind == "on_chain_start" and name in NODE_ACTIVITY:
        yield StatusEvent(state=NODE_ACTIVITY[name], node=name)
        return

    if kind == "on_tool_start":
        yield ToolEvent(status="INVOKED", tool=name or "tool")
        return

    if kind == "on_tool_end":
        payload = _tool_payload(event)
        succeeded = payload is None or payload.get("ok") is not False
        yield ToolEvent(
            status="SUCCEEDED" if succeeded else "FAILED", tool=name or "tool"
        )
        result_config = STRUCTURED_TOOL_RESULTS.get(name)
        if succeeded and payload and result_config:
            result_type, result_key = result_config
            if result_key in payload:
                yield ResultEvent(
                    result_type=result_type,
                    tool=name,
                    data=payload[result_key],
                )
        return

    if kind == "on_tool_error":
        yield ToolEvent(status="FAILED", tool=name or "tool")
        return

    if kind == "on_chat_model_stream":
        graph_node = event.get("metadata", {}).get("langgraph_node")
        if graph_node is not None and graph_node not in RESPONSE_NODES:
            return
        chunk = event["data"]["chunk"]
        content = chunk_text(getattr(chunk, "content", ""))
        if content:
            yield TokenEvent(content=content)
        return

    if kind == "on_chat_model_end":
        graph_node = event.get("metadata", {}).get("langgraph_node")
        if graph_node not in RESPONSE_NODES:
            return
        output = event.get("data", {}).get("output")
        if getattr(output, "tool_calls", None):
            return
        content = chunk_text(getattr(output, "content", ""))
        quick_replies = quick_replies_for_text(content)
        if quick_replies:
            yield quick_replies


def user_safe_error() -> ErrorEvent:
    return ErrorEvent(
        message=(
            "Something went wrong on our side. The rest of TripWeaver is "
            "still up - please try again."
        )
    )


def done_event() -> DoneEvent:
    return DoneEvent()
