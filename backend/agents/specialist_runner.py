"""Shared specialist-agent execution loop."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import SystemMessage, ToolMessage

from agents.entity import ActivityState, ToolCallStatus, TripWeaverState
from agents.history import recent_history
from agents.llm import get_agent_llm
from agents.mcp_client import ServerName, get_tools_for
from agents.tool_results import extract_booking_confirmation, fence_untrusted

MAX_TOOL_ROUNDS = 3


@dataclass(frozen=True)
class SpecialistConfig:
    server: ServerName
    system_prompt: str
    agent_name: str


def unavailable_tool_prompt() -> str:
    return (
        "\n\nThe live search/booking service is temporarily unavailable. Tell the "
        "traveller plainly that you can't fetch live results right now and suggest "
        "they try again shortly - never invent results."
    )


async def run_specialist(state: TripWeaverState, config: SpecialistConfig) -> dict:
    tools = await get_tools_for(config.server)
    llm = get_agent_llm()
    bound = llm.bind_tools(tools) if tools else llm

    system = config.system_prompt
    if not tools:
        system += unavailable_tool_prompt()

    conversation = [SystemMessage(content=system), *recent_history(state)]
    new_messages: list = []
    tool_records: list = []
    activity = ActivityState.RESPONDING
    booking_confirmation: dict[str, Any] | None = None

    for _round in range(MAX_TOOL_ROUNDS):
        response = await bound.ainvoke(conversation)
        new_messages.append(response)
        conversation.append(response)

        calls = getattr(response, "tool_calls", None) or []
        if not calls:
            break

        for call in calls:
            tool = next((tool_item for tool_item in tools if tool_item.name == call["name"]), None)
            activity = ActivityState.BOOKING if "book" in call["name"] else ActivityState.SEARCHING
            detail = None
            if tool is None:
                content = fence_untrusted(f"Tool '{call['name']}' is not available right now.")
                call_status = ToolCallStatus.FAILED
            else:
                try:
                    raw_result = await tool.ainvoke(call["args"])
                    content = fence_untrusted(str(raw_result))
                    call_status = ToolCallStatus.SUCCEEDED
                    extracted = extract_booking_confirmation(
                        tool_name=call["name"], server=config.server, raw_result=raw_result
                    )
                    if extracted:
                        booking_confirmation = extracted
                        detail = str(extracted.get("confirmation_number") or "simulated booking confirmed")
                except Exception as exc:  # noqa: BLE001 - never crash a user turn on tool failure
                    content = fence_untrusted(f"The {call['name']} call failed: {exc}")
                    call_status = ToolCallStatus.FAILED

            tool_records.append(
                {
                    "tool_name": call["name"],
                    "server": config.server,
                    "status": call_status,
                    "detail": detail,
                }
            )
            tool_message = ToolMessage(content=content, tool_call_id=call["id"])
            new_messages.append(tool_message)
            conversation.append(tool_message)
    else:
        final = await llm.ainvoke(
            [*conversation, SystemMessage(content="Summarise what you found for the traveller now.")]
        )
        new_messages.append(final)

    result = {
        "messages": new_messages,
        "active_agent": config.agent_name,
        "activity": activity,
        "tool_calls": tool_records,
    }
    if booking_confirmation is not None:
        result["booking_confirmation"] = booking_confirmation
    return result
