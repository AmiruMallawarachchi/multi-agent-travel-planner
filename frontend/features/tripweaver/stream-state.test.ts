import { describe, expect, it } from "vitest"

import { createConversation } from "./conversations"
import { applyStreamEvent, createRuntimeState } from "./stream-state"

describe("stream state", () => {
  it("turns SSE events into visible assistant and MCP state", () => {
    const conversation = createConversation(new Date("2026-07-13T08:00:00.000Z"), "trip")
    conversation.messages.push({
      id: "assistant-turn",
      role: "assistant",
      content: "",
      createdAt: "2026-07-13T08:01:00.000Z",
      tools: [],
    })
    let state = { conversation, runtime: createRuntimeState(true) }

    state = applyStreamEvent(state, "assistant-turn", {
      type: "session",
      session_id: "session-1",
    })
    state = applyStreamEvent(state, "assistant-turn", {
      type: "tool",
      status: "INVOKED",
      tool: "search_flights",
    })
    state = applyStreamEvent(state, "assistant-turn", {
      type: "tool",
      status: "SUCCEEDED",
      tool: "search_flights",
    })
    state = applyStreamEvent(state, "assistant-turn", {
      type: "token",
      content: "Two flights found.",
    })

    expect(state.conversation.sessionId).toBe("session-1")
    expect(state.runtime.services.flight.status).toBe("completed")
    expect(state.conversation.messages.at(-1)).toMatchObject({
      content: "Two flights found.",
      tools: [{ label: "Flight search", server: "Flight MCP", status: "completed" }],
    })
  })

  it("marks unavailable services explicitly", () => {
    const runtime = createRuntimeState(true)

    expect(runtime.services.itinerary.status).toBe("unavailable")
    expect(runtime.services.weather.status).toBe("unavailable")
    expect(runtime.services.currency.status).toBe("unavailable")
    expect(runtime.services.location.status).toBe("unavailable")
  })
})
