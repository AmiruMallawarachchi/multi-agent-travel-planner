"""Conversation-window helpers used by graph nodes."""
from __future__ import annotations

from langchain_core.messages import ToolMessage

from agents.entity import TripWeaverState

# LangGraph can retain the full transcript per thread, but every LLM call only
# needs a bounded tail. This keeps long chats predictable in token cost.
MAX_HISTORY_MESSAGES = 16


def recent_history(state: TripWeaverState) -> list:
    """Return a bounded tail that is still a *valid* message sequence.

    A ToolMessage is only legal immediately after the AIMessage whose
    tool_calls it answers. A fixed-size tail can slice that pair in half and
    leave a leading orphan, which providers reject outright - failing the whole
    turn once a conversation grows past the window. Drop leading orphans.
    """
    window = state["messages"][-MAX_HISTORY_MESSAGES:]
    first_valid = 0
    while first_valid < len(window) and isinstance(window[first_valid], ToolMessage):
        first_valid += 1
    return window[first_valid:]
