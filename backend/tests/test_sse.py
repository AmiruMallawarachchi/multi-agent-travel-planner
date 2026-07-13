from __future__ import annotations

import json

from api.schemas import StatusEvent, TokenEvent
from api.sse import chunk_text, encode_sse, stream_events_from_graph_event, user_safe_error


class Chunk:
    def __init__(self, content):
        self.content = content


def test_encode_sse_serializes_one_data_frame():
    frame = encode_sse(StatusEvent(state="ROUTING", node="classify_intent"))

    assert frame.endswith("\n\n")
    payload = json.loads(frame.removeprefix("data: ").strip())
    assert payload == {"type": "status", "state": "ROUTING", "node": "classify_intent"}


def test_chunk_text_normalizes_provider_chunk_shapes():
    assert chunk_text("hello") == "hello"
    assert chunk_text([{"text": "hel"}, "lo", {"ignored": True}]) == "hello"
    assert chunk_text(None) == ""


def test_stream_events_from_graph_event_maps_chain_tool_and_token_events():
    events = list(stream_events_from_graph_event({"event": "on_chain_start", "name": "hotel"}))
    assert events[0].model_dump() == {"type": "status", "state": "SEARCHING", "node": "hotel"}

    events = list(stream_events_from_graph_event({"event": "on_tool_error", "name": "search_hotels"}))
    assert events[0].model_dump() == {"type": "tool", "status": "FAILED", "tool": "search_hotels"}

    events = list(
        stream_events_from_graph_event(
            {
                "event": "on_chat_model_stream",
                "metadata": {"langgraph_node": "general_qa"},
                "data": {"chunk": Chunk([{"text": "hi"}])},
            }
        )
    )
    assert events == [TokenEvent(content="hi")]


def test_stream_events_from_graph_event_hides_router_model_output():
    event = {
        "event": "on_chat_model_stream",
        "metadata": {"langgraph_node": "classify_intent"},
        "data": {"chunk": Chunk("general_qa")},
    }

    assert list(stream_events_from_graph_event(event)) == []


def test_stream_events_from_graph_event_ignores_unknown_events():
    assert list(stream_events_from_graph_event({"event": "not_used"})) == []


def test_user_safe_error_does_not_leak_internal_exception_details():
    event = user_safe_error()
    assert "Something went wrong" in event.message
    assert "Traceback" not in event.message
