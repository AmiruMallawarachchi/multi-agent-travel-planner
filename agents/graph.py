"""
agents/graph.py
LangGraph StateGraph definition for TripWeaver.

Topology
--------
  START
    │
    ▼
  detect_intent  ←── classifies user query into hotel | flight | general
    │
    ├── "hotel"   → hotel_node   → END
    ├── "flight"  → flight_node  → END
    └── "general" → general_qa   → END

The intent router is a conditional edge function that reads state["intent"]
(set by detect_intent_node) and returns the name of the next node to run.
"""

from langgraph.graph import StateGraph, START, END
from agents.entity import AgentState
from agents.nodes import (
    detect_intent_node,
    general_qa_node,
    hotel_node,
    flight_node,
)


def _route_by_intent(state: AgentState) -> str:
    """
    Conditional edge function: reads the detected intent from state and
    returns the name of the next node to execute.

    Called automatically by LangGraph after detect_intent_node completes.
    """
    intent = state.get("intent", "general")
    # Ensure we always route to a valid node even if classification is unexpected
    if intent not in ("hotel", "flight", "general"):
        return "general"
    return intent


def build_graph() -> StateGraph:
    """Build and compile the TripWeaver LangGraph StateGraph."""
    builder = StateGraph(AgentState)

    # ── Register nodes ─────────────────────────────────────────────
    builder.add_node("detect_intent", detect_intent_node)
    builder.add_node("hotel", hotel_node)
    builder.add_node("flight", flight_node)
    builder.add_node("general_qa", general_qa_node)

    # ── Wire edges ─────────────────────────────────────────────────
    # Entry point: always run intent detection first
    builder.add_edge(START, "detect_intent")

    # Intent router: conditional branch after detection
    builder.add_conditional_edges(
        "detect_intent",
        _route_by_intent,
        {
            "hotel":   "hotel",
            "flight":  "flight",
            "general": "general_qa",
        },
    )

    # All specialist nodes terminate the graph
    builder.add_edge("hotel",      END)
    builder.add_edge("flight",     END)
    builder.add_edge("general_qa", END)

    return builder.compile()


# Singleton compiled graph — imported by main.py and frontend.py
travel_graph = build_graph()
