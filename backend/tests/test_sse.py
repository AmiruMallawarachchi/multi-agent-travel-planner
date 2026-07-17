from __future__ import annotations

import json

from langchain_core.messages import AIMessage

from api.schemas import QuickRepliesEvent, ResultEvent, StatusEvent, TokenEvent
from api.sse import (
    chunk_text,
    encode_sse,
    quick_replies_for_text,
    stream_events_from_graph_event,
    user_safe_error,
)


class Chunk:
    def __init__(self, content):
        self.content = content
        self.tool_calls = []


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
    events = list(
        stream_events_from_graph_event({"event": "on_chain_start", "name": "hotel"})
    )
    assert events[0].model_dump() == {
        "type": "status",
        "state": "SEARCHING",
        "node": "hotel",
    }

    events = list(
        stream_events_from_graph_event(
            {"event": "on_tool_error", "name": "search_hotels"}
        )
    )
    assert events[0].model_dump() == {
        "type": "tool",
        "status": "FAILED",
        "tool": "search_hotels",
    }

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


def test_stream_events_from_graph_event_emits_normalized_structured_results():
    event = {
        "event": "on_tool_end",
        "name": "get_weather_forecast",
        "data": {
            "output": [
                {
                    "type": "text",
                    "text": (
                        '{"ok": true, "weather": '
                        '{"location": {"name": "Tokyo"}, "daily": []}}'
                    ),
                }
            ]
        },
    }

    events = list(stream_events_from_graph_event(event))

    assert events[0].model_dump() == {
        "type": "tool",
        "status": "SUCCEEDED",
        "tool": "get_weather_forecast",
    }
    assert events[1] == ResultEvent(
        result_type="weather",
        tool="get_weather_forecast",
        data={"location": {"name": "Tokyo"}, "daily": []},
    )


def test_structured_result_is_not_emitted_for_failed_tool_payload():
    event = {
        "event": "on_tool_end",
        "name": "convert_currency",
        "data": {"output": {"ok": False, "error": "provider unavailable"}},
    }

    events = list(stream_events_from_graph_event(event))

    assert len(events) == 1
    assert events[0].type == "tool"


def test_stream_events_from_graph_event_hides_router_model_output():
    event = {
        "event": "on_chat_model_stream",
        "metadata": {"langgraph_node": "classify_intent"},
        "data": {"chunk": Chunk("general_qa")},
    }

    assert list(stream_events_from_graph_event(event)) == []


def test_model_end_emits_numbered_choices_for_one_planning_question():
    event = {
        "event": "on_chat_model_end",
        "metadata": {"langgraph_node": "itinerary"},
        "data": {"output": Chunk("How many travellers will join this trip?")},
    }

    events = list(stream_events_from_graph_event(event))

    assert len(events) == 1
    assert isinstance(events[0], QuickRepliesEvent)
    assert [option.label for option in events[0].options] == [
        "Solo",
        "Two people",
        "Family",
        "Group",
    ]
    assert events[0].allow_custom_answer is True


def test_guided_intake_emits_exact_question_progress_and_choices():
    message = AIMessage(
        content="Which expenses should the estimate include?",
        additional_kwargs={
            "tripweaver_quick_replies": {
                "question_id": "trip-budget-expenses",
                "step": 2,
                "total_steps": 3,
                "allow_custom_answer": True,
                "options": [
                    {
                        "id": "complete",
                        "label": "Complete trip",
                        "value": "Include every category.",
                    }
                ],
            }
        },
    )

    events = list(
        stream_events_from_graph_event(
            {
                "event": "on_chain_end",
                "name": "trip_budget",
                "data": {"output": {"messages": [message]}},
            }
        )
    )

    assert events[0] == TokenEvent(
        content="Which expenses should the estimate include?"
    )
    assert events[1] == QuickRepliesEvent(
        question_id="trip-budget-expenses",
        step=2,
        total_steps=3,
        options=[
            {
                "id": "complete",
                "label": "Complete trip",
                "value": "Include every category.",
            }
        ],
    )


def test_final_guided_answer_switches_from_intake_to_response_status():
    events = list(
        stream_events_from_graph_event(
            {
                "event": "on_chat_model_start",
                "metadata": {"langgraph_node": "trip_budget"},
            }
        )
    )

    assert events == [StatusEvent(state="RESPONDING", node="trip_budget")]


def test_quick_reply_detection_ignores_statements_and_tool_call_rounds():
    assert quick_replies_for_text("Your itinerary is ready.") is None
    output = Chunk("What is your budget?")
    output.tool_calls = [{"name": "create_itinerary"}]
    assert list(
        stream_events_from_graph_event(
            {
                "event": "on_chat_model_end",
                "metadata": {"langgraph_node": "itinerary"},
                "data": {"output": output},
            }
        )
    ) == []


def test_stream_events_from_graph_event_ignores_unknown_events():
    assert list(stream_events_from_graph_event({"event": "not_used"})) == []


def test_user_safe_error_does_not_leak_internal_exception_details():
    event = user_safe_error()
    assert "Something went wrong" in event.message
    assert "Traceback" not in event.message
