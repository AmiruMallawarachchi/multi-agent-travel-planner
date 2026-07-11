"""
agents/entity.py
Shared state schema passed between all LangGraph nodes in TripWeaver.
"""

from __future__ import annotations
from typing import TypedDict, Optional, Annotated
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    The single source of truth shared across all agent nodes.

    Fields
    ------
    messages        : Full conversation history (HumanMessage / AIMessage).
                      Uses `add_messages` reducer so appends accumulate correctly.
    user_query      : The raw text of the current user turn.
    intent          : Detected intent — "hotel" | "flight" | "general".
    hotel_results   : Raw data returned by hotel MCP tools (list / search).
    flight_results  : Raw data returned by flight MCP tools (list / search).
    booking_result  : Confirmation payload returned by a booking MCP tool.
    agent_activity  : Current activity label streamed to the UI:
                      "ROUTING" | "SEARCHING" | "BOOKING" | "RESPONDING" | "CLARIFYING"
    error           : Human-readable error string if an MCP call failed; None otherwise.
    """

    messages: Annotated[list, add_messages]
    user_query: str
    intent: str
    hotel_results: list
    flight_results: list
    booking_result: dict
    agent_activity: str
    error: Optional[str]
