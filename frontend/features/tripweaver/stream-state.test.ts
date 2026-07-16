import { describe, expect, it } from "vitest"

import { createConversation } from "./conversations"
import { applyStreamEvent, createRuntimeState } from "./stream-state"

const AVAILABLE_SERVICES = {
  "hotel-mcp": "available",
  "flight-mcp": "available",
  "itinerary-mcp": "available",
  "weather-mcp": "available",
  "currency-mcp": "available",
  "location-mcp": "available",
} as const

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
    let state = {
      conversation,
      runtime: createRuntimeState(true, AVAILABLE_SERVICES),
    }

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

  it("uses backend health to distinguish available and unavailable services", () => {
    const runtime = createRuntimeState(true, {
      ...AVAILABLE_SERVICES,
      "location-mcp": "unavailable",
    })

    expect(runtime.services.itinerary.status).toBe("idle")
    expect(runtime.services.weather.status).toBe("idle")
    expect(runtime.services.currency.status).toBe("idle")
    expect(runtime.services.location.status).toBe("unavailable")
  })

  it("maps weather tools and stores structured results on the assistant message", () => {
    const conversation = createConversation(
      new Date("2026-07-13T08:00:00.000Z"),
      "weather",
    )
    conversation.messages.push({
      id: "assistant-turn",
      role: "assistant",
      content: "",
      createdAt: "2026-07-13T08:01:00.000Z",
      tools: [],
      results: [],
    })
    let state = {
      conversation,
      runtime: createRuntimeState(true, AVAILABLE_SERVICES),
    }

    state = applyStreamEvent(state, "assistant-turn", {
      type: "tool",
      status: "INVOKED",
      tool: "get_weather_forecast",
    })
    state = applyStreamEvent(state, "assistant-turn", {
      type: "result",
      result_type: "weather",
      tool: "get_weather_forecast",
      data: { location: { name: "Tokyo" }, daily: [] },
    })

    expect(state.runtime.activeAgent).toBe("Weather agent")
    expect(state.runtime.services.weather.status).toBe("running")
    expect(state.conversation.messages.at(-1)?.tools).toEqual([
      expect.objectContaining({ label: "Weather forecast", server: "Weather MCP" }),
    ])
    expect(state.conversation.messages.at(-1)?.results).toEqual([
      {
        type: "weather",
        tool: "get_weather_forecast",
        data: { location: { name: "Tokyo" }, daily: [] },
      },
    ])
  })

  it("hydrates trip context from a structured itinerary", () => {
    const conversation = createConversation(
      new Date("2026-07-13T08:00:00.000Z"),
      "itinerary",
    )
    conversation.messages.push({
      id: "assistant-turn",
      role: "assistant",
      content: "",
      createdAt: "2026-07-13T08:01:00.000Z",
    })
    const state = applyStreamEvent(
      {
        conversation,
        runtime: createRuntimeState(true, AVAILABLE_SERVICES),
      },
      "assistant-turn",
      {
        type: "result",
        result_type: "itinerary",
        tool: "create_itinerary",
        data: {
          destination: "Tokyo",
          start_date: "2026-12-10",
          end_date: "2026-12-16",
          travelers: 2,
          budget: { total: 3000, currency: "USD" },
          interests: ["food", "culture"],
        },
      },
    )

    expect(state.conversation.tripContext).toEqual({
      destination: "Tokyo",
      dates: "2026-12-10 - 2026-12-16",
      travelers: "2 travellers",
      budget: "USD 3,000",
      preferences: ["food", "culture"],
    })
  })

  it("attaches structured quick replies without changing text messages", () => {
    const conversation = createConversation(
      new Date("2026-07-13T08:00:00.000Z"),
      "clarify",
    )
    conversation.messages.push({
      id: "assistant-turn",
      role: "assistant",
      content: "How many people are travelling?",
      createdAt: "2026-07-13T08:01:00.000Z",
    })

    const state = applyStreamEvent(
      { conversation, runtime: createRuntimeState(true, AVAILABLE_SERVICES) },
      "assistant-turn",
      {
        type: "quick_replies",
        options: [{ id: "two", label: "2 people", value: "2 travellers" }],
        allow_custom_answer: true,
      },
    )

    expect(state.conversation.messages.at(-1)).toMatchObject({
      content: "How many people are travelling?",
      quickReplies: {
        options: [{ id: "two", label: "2 people", value: "2 travellers" }],
        allowCustomAnswer: true,
      },
    })
  })
})
