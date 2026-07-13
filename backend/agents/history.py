"""Conversation-window helpers used by graph nodes."""
from __future__ import annotations

from agents.entity import TripWeaverState

# LangGraph can retain the full transcript per thread, but every LLM call only
# needs a bounded tail. This keeps long chats predictable in token cost.
MAX_HISTORY_MESSAGES = 16


def recent_history(state: TripWeaverState) -> list:
    return state["messages"][-MAX_HISTORY_MESSAGES:]
