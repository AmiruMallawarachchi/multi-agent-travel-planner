"""
agents/entity.py
Shared state schema for the TripWeaver LangGraph workflow (SRS section 3 & 7).

Every node in the graph reads and writes ONLY this schema - there is no
private, side-channel state anywhere in the system. This is what SRS
section 7 means by "the schema is the single source of truth for what one
agent knows about another's work."
"""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Optional, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class Intent(str, Enum):
    """Output space of the router / classify_intent node (SRS section 2)."""
    GENERAL_QA = "general_qa"
    HOTEL = "hotel"
    FLIGHT = "flight"
    CLARIFY = "clarify"
    END = "end"


class ActivityState(str, Enum):
    """Mirrors SRS section 6 - Agent Activity & Tool-Call Lifecycle exactly,
    so the frontend's activity indicator is a 1:1 rendering of this enum."""
    ROUTING = "ROUTING"
    SEARCHING = "SEARCHING"
    BOOKING = "BOOKING"
    RESPONDING = "RESPONDING"
    CLARIFYING = "CLARIFYING"


class ToolCallStatus(str, Enum):
    """Mirrors SRS section 6 - Tool-Call Status table."""
    INVOKED = "INVOKED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class ToolCallRecord(TypedDict):
    tool_name: str
    server: str  # "hotel-mcp" | "flight-mcp"
    status: ToolCallStatus
    detail: Optional[str]


class TripWeaverState(TypedDict):
    # Full conversation. `add_messages` is LangGraph's reducer: nodes return
    # *new* messages and LangGraph appends them, instead of every node having
    # to know and re-return the whole history.
    messages: Annotated[list[AnyMessage], add_messages]

    # Routing signals - written by classify_intent, read by every downstream
    # node and by the FastAPI layer to drive the activity indicator.
    intent: Optional[Intent]
    active_agent: Optional[str]
    activity: Optional[ActivityState]

    # Missing-input handling (SRS section 4 step 6 / section 7).
    missing_fields: list[str]
    clarification_question: Optional[str]

    # Findings gathered from MCP tools this turn (SRS section 3: Hotel /
    # Flight / Booking entities).
    hotel_results: list[dict[str, Any]]
    flight_results: list[dict[str, Any]]
    booking_confirmation: Optional[dict[str, Any]]

    # Every MCP call this turn, success or failure - the backbone of the
    # graceful-degradation story defended in the viva (SRS section 6 / 11).
    tool_calls: list[ToolCallRecord]

    # Thread identity. Doubles as the LangGraph checkpointer thread_id, which
    # is what gives TripWeaver cross-turn memory for free (SRS section 9,
    # stretch goal "carry conversation context across turns").
    session_id: str


def new_state(session_id: str, user_message: str) -> dict:
    """Convenience constructor for a fresh turn's input to `graph.ainvoke`/
    `graph.astream_events`. Only `messages` needs seeding - every other key
    has a sane default and LangGraph merges partial node returns in on top."""
    return {
        "messages": [{"role": "user", "content": user_message}],
        "intent": None,
        "active_agent": None,
        "activity": None,
        "missing_fields": [],
        "clarification_question": None,
        "hotel_results": [],
        "flight_results": [],
        "booking_confirmation": None,
        "tool_calls": [],
        "session_id": session_id,
    }
