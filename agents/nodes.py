"""
agents/nodes.py
LangGraph node functions for TripWeaver's three agents.

Node flow
---------
  START → detect_intent_node
             ↓ (conditional edge based on state["intent"])
     ┌───────┬───────┐
     ▼       ▼       ▼
  hotel   flight  general_qa
     └───────┴───────┘
             ↓
            END

Each specialist node:
  1. Binds its MCP tools to the LLM.
  2. Invokes the LLM — if it wants to call a tool, executes the tool call.
  3. Feeds tool results back to the LLM for a final composed response.
  4. Returns the updated AgentState.

Failures in MCP tool calls are caught at the tool layer (agents/tools.py).
If a tool returns an error JSON, the LLM sees it and responds gracefully.
"""

from __future__ import annotations
import json
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from agents.entity import AgentState
from agents.llm import get_llm
from agents.prompts import (
    INTENT_ROUTER_PROMPT,
    GENERAL_QA_PROMPT,
    HOTEL_AGENT_PROMPT,
    FLIGHT_AGENT_PROMPT,
)
from agents.tools import HOTEL_TOOLS, FLIGHT_TOOLS


# ─────────────────────────────────────────────────────────────
# Helper — execute one round of tool calls
# ─────────────────────────────────────────────────────────────

async def _run_tool_calls(ai_message: AIMessage, tools: list) -> list[ToolMessage]:
    """Execute all tool_calls on an AIMessage; return ToolMessage list."""
    tool_map = {t.name: t for t in tools}
    tool_messages: list[ToolMessage] = []

    for tc in ai_message.tool_calls:
        tool_name = tc["name"]
        tool_args = tc["args"]
        tool_id = tc["id"]

        tool_fn = tool_map.get(tool_name)
        if tool_fn is None:
            content = json.dumps({"error": f"Unknown tool: {tool_name}"})
        else:
            try:
                content = await tool_fn.ainvoke(tool_args)
                # Ensure content is a string
                if not isinstance(content, str):
                    content = json.dumps(content)
            except Exception as exc:
                content = json.dumps({"error": str(exc)})

        tool_messages.append(ToolMessage(content=content, tool_call_id=tool_id))

    return tool_messages


# ─────────────────────────────────────────────────────────────
# Intent Detection Node
# ─────────────────────────────────────────────────────────────

def detect_intent_node(state: AgentState) -> dict:
    """
    Classify the user's query into one of: hotel | flight | general.
    Uses a lightweight, non-streaming LLM call.
    Updates state["intent"] and state["agent_activity"].
    """
    llm = get_llm(streaming=False)
    messages = [
        SystemMessage(content=INTENT_ROUTER_PROMPT),
        HumanMessage(content=state["user_query"]),
    ]
    response = llm.invoke(messages)

    raw = response.content.strip().lower()
    if "hotel" in raw:
        intent = "hotel"
    elif "flight" in raw:
        intent = "flight"
    else:
        intent = "general"

    return {
        "intent": intent,
        "agent_activity": "ROUTING",
    }


# ─────────────────────────────────────────────────────────────
# General QA Node
# ─────────────────────────────────────────────────────────────

async def general_qa_node(state: AgentState) -> dict:
    """
    Handle general travel questions without any MCP tool calls.
    Uses the full conversation history for context-aware answers.
    """
    llm = get_llm(streaming=True)
    messages = [SystemMessage(content=GENERAL_QA_PROMPT)] + list(state["messages"])
    response = await llm.ainvoke(messages)

    return {
        "messages": [response],
        "agent_activity": "RESPONDING",
    }


# ─────────────────────────────────────────────────────────────
# Hotel Agent Node
# ─────────────────────────────────────────────────────────────

async def hotel_node(state: AgentState) -> dict:
    """
    Hotel specialist: decides which hotel MCP tool to call, executes it,
    then composes a user-facing response from the results.

    Routing:
      - LLM with bound hotel tools decides autonomously which tool to call
        (list_hotels / search_hotels / book_hotel) and with what parameters.
      - If the LLM asks for a tool call → execute → feed result back → final answer.
      - If no tool call (e.g., follow-up question) → return LLM response directly.
    """
    llm = get_llm(streaming=True)
    llm_with_tools = llm.bind_tools(HOTEL_TOOLS)

    messages = [SystemMessage(content=HOTEL_AGENT_PROMPT)] + list(state["messages"])
    update: dict = {"agent_activity": "SEARCHING"}

    # First LLM call — may produce tool_calls or a direct response
    first_response: AIMessage = await llm_with_tools.ainvoke(messages)

    if not first_response.tool_calls:
        # No tool calls — LLM is asking a follow-up or giving a direct answer
        return {
            **update,
            "messages": [first_response],
            "agent_activity": "CLARIFYING" if "?" in first_response.content else "RESPONDING",
        }

    # Execute the tool calls
    tool_messages = await _run_tool_calls(first_response, HOTEL_TOOLS)

    # Check if any tool returned a booking result
    is_booking = any(tc["name"] == "book_hotel" for tc in first_response.tool_calls)
    if is_booking:
        update["agent_activity"] = "BOOKING"
        # Try to parse booking result
        for tm in tool_messages:
            try:
                data = json.loads(tm.content)
                if "confirmation_number" in data:
                    update["booking_result"] = data
            except (json.JSONDecodeError, TypeError):
                pass
    else:
        # Store hotel search results
        results = []
        for tm in tool_messages:
            try:
                results.append(json.loads(tm.content))
            except (json.JSONDecodeError, TypeError):
                results.append({"raw": tm.content})
        update["hotel_results"] = results

    # Second LLM call — compose final answer from tool results
    all_messages = messages + [first_response] + tool_messages
    final_response: AIMessage = await llm.ainvoke(all_messages)

    return {
        **update,
        "messages": [final_response],
        "agent_activity": "RESPONDING",
    }


# ─────────────────────────────────────────────────────────────
# Flight Agent Node
# ─────────────────────────────────────────────────────────────

async def flight_node(state: AgentState) -> dict:
    """
    Flight specialist: decides which flight MCP tool to call, executes it,
    then composes a user-facing response from the results.

    Same pattern as hotel_node but uses FLIGHT_TOOLS.
    """
    llm = get_llm(streaming=True)
    llm_with_tools = llm.bind_tools(FLIGHT_TOOLS)

    messages = [SystemMessage(content=FLIGHT_AGENT_PROMPT)] + list(state["messages"])
    update: dict = {"agent_activity": "SEARCHING"}

    first_response: AIMessage = await llm_with_tools.ainvoke(messages)

    if not first_response.tool_calls:
        return {
            **update,
            "messages": [first_response],
            "agent_activity": "CLARIFYING" if "?" in first_response.content else "RESPONDING",
        }

    tool_messages = await _run_tool_calls(first_response, FLIGHT_TOOLS)

    is_booking = any(tc["name"] == "book_flight" for tc in first_response.tool_calls)
    if is_booking:
        update["agent_activity"] = "BOOKING"
        for tm in tool_messages:
            try:
                data = json.loads(tm.content)
                if "confirmation_number" in data:
                    update["booking_result"] = data
            except (json.JSONDecodeError, TypeError):
                pass
    else:
        results = []
        for tm in tool_messages:
            try:
                results.append(json.loads(tm.content))
            except (json.JSONDecodeError, TypeError):
                results.append({"raw": tm.content})
        update["flight_results"] = results

    all_messages = messages + [first_response] + tool_messages
    final_response: AIMessage = await llm.ainvoke(all_messages)

    return {
        **update,
        "messages": [final_response],
        "agent_activity": "RESPONDING",
    }
