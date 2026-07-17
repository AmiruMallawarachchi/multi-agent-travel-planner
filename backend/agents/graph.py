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
    currency_node,
    flight_node,
    general_qa_node,
    hotel_node,
    itinerary_node,
    location_node,
    route_from_intent,
    trip_budget_node,
    weather_node,
)


def build_graph():
    builder = StateGraph(TripWeaverState)

    builder.add_node("classify_intent", classify_intent)
    builder.add_node("general_qa", general_qa_node)
    builder.add_node("hotel", hotel_node)
    builder.add_node("flight", flight_node)
    builder.add_node("itinerary", itinerary_node)
    builder.add_node("weather", weather_node)
    builder.add_node("currency", currency_node)
    builder.add_node("location", location_node)
    builder.add_node("trip_budget", trip_budget_node)
    builder.add_node("clarify", clarify_node)

    builder.add_edge(START, "classify_intent")
    builder.add_conditional_edges(
        "classify_intent",
        route_from_intent,
        {
            Intent.GENERAL_QA.value: "general_qa",
            Intent.HOTEL.value: "hotel",
            Intent.FLIGHT.value: "flight",
            Intent.ITINERARY.value: "itinerary",
            Intent.WEATHER.value: "weather",
            Intent.CURRENCY.value: "currency",
            Intent.LOCATION.value: "location",
            Intent.TRIP_BUDGET.value: "trip_budget",
            Intent.CLARIFY.value: "clarify",
            Intent.END.value: END,
        },
    )
    builder.add_edge("general_qa", END)
    builder.add_edge("hotel", END)
    builder.add_edge("flight", END)
    builder.add_edge("itinerary", END)
    builder.add_edge("weather", END)
    builder.add_edge("currency", END)
    builder.add_edge("location", END)
    builder.add_edge("trip_budget", END)
    builder.add_edge("clarify", END)

    # MemorySaver gives per-thread (per session_id) conversation memory
    # across turns for free - SRS section 9 stretch goal ("carry
    # conversation context across turns so the traveller can refine
    # without repeating themselves"). Swap for a Postgres/Redis checkpointer
    # if you need memory to survive a backend restart.
    return builder.compile(checkpointer=MemorySaver())


graph = build_graph()
