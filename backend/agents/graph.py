"""
agents/graph.py
Wires the shared state schema and node functions into an intent-routed
LangGraph StateGraph (SRS section 2 / 4 / 9-E2).
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agents.entity import Intent, TripWeaverState
from agents.nodes import (
    classify_intent,
    clarify_node,
    flight_node,
    general_qa_node,
    hotel_node,
    route_from_intent,
)


def build_graph():
    builder = StateGraph(TripWeaverState)

    builder.add_node("classify_intent", classify_intent)
    builder.add_node("general_qa", general_qa_node)
    builder.add_node("hotel", hotel_node)
    builder.add_node("flight", flight_node)
    builder.add_node("clarify", clarify_node)

    builder.add_edge(START, "classify_intent")
    builder.add_conditional_edges(
        "classify_intent",
        route_from_intent,
        {
            Intent.GENERAL_QA.value: "general_qa",
            Intent.HOTEL.value: "hotel",
            Intent.FLIGHT.value: "flight",
            Intent.CLARIFY.value: "clarify",
            Intent.END.value: END,
        },
    )
    builder.add_edge("general_qa", END)
    builder.add_edge("hotel", END)
    builder.add_edge("flight", END)
    builder.add_edge("clarify", END)

    # MemorySaver gives per-thread (per session_id) conversation memory
    # across turns for free - SRS section 9 stretch goal ("carry
    # conversation context across turns so the traveller can refine
    # without repeating themselves"). Swap for a Postgres/Redis checkpointer
    # if you need memory to survive a backend restart.
    return builder.compile(checkpointer=MemorySaver())


graph = build_graph()
