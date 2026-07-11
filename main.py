"""
main.py
TripWeaver FastAPI backend.

Endpoints
---------
  GET  /health   — liveness check
  POST /chat     — streaming chat endpoint (Server-Sent Events)

The /chat endpoint:
  1. Accepts a user message and conversation history.
  2. Builds the initial AgentState.
  3. Streams LangGraph astream_events() as SSE lines to the client.
  4. Each SSE event has a `type` field:
       "activity" — agent status update (ROUTING / SEARCHING / BOOKING …)
       "token"    — one streamed LLM token
       "error"    — user-friendly error from a failed MCP call
       "done"     — signals end of response

Run:
  uvicorn main:app --reload --port 8000
"""

from __future__ import annotations
import json
import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from agents.graph import travel_graph
from agents.entity import AgentState

app = FastAPI(
    title="TripWeaver API",
    description="MCP-Based Multi-Agent Travel Planner backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────

class HistoryTurn(BaseModel):
    role: str        # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[HistoryTurn] = []


# ─────────────────────────────────────────────────────────────
# Helper: SSE line builder
# ─────────────────────────────────────────────────────────────

def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


# ─────────────────────────────────────────────────────────────
# Activity label map  (LangGraph node name → UI message)
# ─────────────────────────────────────────────────────────────

_ACTIVITY_LABELS: dict[str, str] = {
    "detect_intent": "🔀 Routing your request...",
    "hotel":         "🏨 Searching hotel suggestions...",
    "flight":        "✈️ Searching flight options...",
    "general_qa":    "💬 Thinking...",
}

_BOOKING_LABELS: dict[str, str] = {
    "hotel":  "🏨 Booking your hotel...",
    "flight": "✈️ Booking your flight...",
}

# Nodes whose LLM output tokens we stream to the client
_STREAMING_NODES = {"hotel", "flight", "general_qa"}


# ─────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "TripWeaver"}


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Streaming chat endpoint.
    Accepts a user message + conversation history; streams SSE events.
    """

    async def generate():
        # ── Build LangChain message history ───────────────────────
        history_messages = []
        for turn in request.history:
            if turn.role == "user":
                history_messages.append(HumanMessage(content=turn.content))
            elif turn.role == "assistant":
                history_messages.append(AIMessage(content=turn.content))
        history_messages.append(HumanMessage(content=request.message))

        # ── Initial AgentState ─────────────────────────────────────
        initial_state: AgentState = {
            "messages":       history_messages,
            "user_query":     request.message,
            "intent":         "",
            "hotel_results":  [],
            "flight_results": [],
            "booking_result": {},
            "agent_activity": "ROUTING",
            "error":          None,
        }

        # ── Stream graph events ────────────────────────────────────
        try:
            async for event in travel_graph.astream_events(initial_state, version="v2"):
                etype = event.get("event", "")
                node  = event.get("metadata", {}).get("langgraph_node", "")

                # ·· Agent activity label ··
                if etype == "on_chain_start" and node in _ACTIVITY_LABELS:
                    yield _sse({"type": "activity", "content": _ACTIVITY_LABELS[node]})

                # ·· Booking activity override ··
                elif etype == "on_chain_end" and node in ("hotel", "flight"):
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict):
                        activity = output.get("agent_activity", "")
                        if activity == "BOOKING":
                            yield _sse({"type": "activity", "content": _BOOKING_LABELS.get(node, "📋 Processing booking...")})
                        # Surface errors
                        if output.get("error"):
                            yield _sse({"type": "error", "content": output["error"]})

                # ·· Streamed LLM tokens (final response nodes only) ··
                elif etype == "on_chat_model_stream" and node in _STREAMING_NODES:
                    chunk = event["data"].get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield _sse({"type": "token", "content": chunk.content})

        except Exception as exc:
            # Graceful top-level failure — never crash the connection
            yield _sse({
                "type": "error",
                "content": f"Sorry, something went wrong: {str(exc)}. Please try again.",
            })

        yield _sse({"type": "done"})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering for SSE
        },
    )
