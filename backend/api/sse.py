"""SSE encoding and LangGraph event normalization."""
from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from agents.entity import ActivityState
from api.schemas import DoneEvent, ErrorEvent, StatusEvent, StreamEvent, TokenEvent, ToolEvent

NODE_ACTIVITY = {
    "classify_intent": ActivityState.ROUTING.value,
    "general_qa": ActivityState.RESPONDING.value,
    "hotel": ActivityState.SEARCHING.value,
    "flight": ActivityState.SEARCHING.value,
    "clarify": ActivityState.CLARIFYING.value,
}
RESPONSE_NODES = frozenset(NODE_ACTIVITY) - {"classify_intent"}


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
        yield ToolEvent(status="SUCCEEDED", tool=name or "tool")
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


def user_safe_error() -> ErrorEvent:
    return ErrorEvent(
        message=(
            "Something went wrong on our side. The rest of TripWeaver is "
            "still up - please try again."
        )
    )


def done_event() -> DoneEvent:
    return DoneEvent()
