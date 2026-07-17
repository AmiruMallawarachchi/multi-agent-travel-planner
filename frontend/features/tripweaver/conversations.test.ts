import { describe, expect, it } from "vitest"

import {
  createConversation,
  deriveConversationTitle,
  exportConversation,
  groupConversations,
  parseStoredConversations,
  searchConversations,
} from "./conversations"

describe("conversation helpers", () => {
  it("creates a clean conversation with a welcome message", () => {
    const conversation = createConversation(new Date("2026-07-13T08:00:00.000Z"), "trip-1")

    expect(conversation.id).toBe("trip-1")
    expect(conversation.title).toBe("New trip")
    expect(conversation.messages).toHaveLength(1)
    expect(conversation.messages[0]).toMatchObject({ role: "assistant" })
  })

  it("personalizes a new conversation with the traveller's first name", () => {
    const conversation = createConversation(
      new Date("2026-07-13T08:00:00.000Z"),
      "trip-2",
      "Maya Perera",
    )

    expect(conversation.messages[0].content).toMatch(/^Welcome, Maya\. Hi, I am TripWeaver\./)
  })

  it("derives a concise title from the first request", () => {
    expect(deriveConversationTitle("  Plan   seven days in Tokyo with food tours  ")).toBe(
      "Plan seven days in Tokyo with food tours",
    )
    expect(deriveConversationTitle("A".repeat(80))).toHaveLength(48)
  })

  it("searches titles and message content case-insensitively", () => {
    const tokyo = createConversation(new Date("2026-07-13T08:00:00.000Z"), "tokyo")
    tokyo.title = "Trip to Tokyo"
    const bali = createConversation(new Date("2026-07-12T08:00:00.000Z"), "bali")
    bali.title = "Beach holiday"
    bali.messages.push({
      id: "bali-message",
      role: "user",
      content: "Find a quiet hotel in Bali",
      createdAt: "2026-07-12T08:05:00.000Z",
    })

    expect(searchConversations([tokyo, bali], "tokyo").map(({ id }) => id)).toEqual(["tokyo"])
    expect(searchConversations([tokyo, bali], "BALI").map(({ id }) => id)).toEqual(["bali"])
  })

  it("groups conversations by recency", () => {
    const today = createConversation(new Date("2026-07-13T05:00:00.000Z"), "today")
    const yesterday = createConversation(new Date("2026-07-12T05:00:00.000Z"), "yesterday")
    const older = createConversation(new Date("2026-07-01T05:00:00.000Z"), "older")

    const groups = groupConversations(
      [older, yesterday, today],
      new Date("2026-07-13T12:00:00.000Z"),
    )

    expect(groups.map(({ label, conversations }) => [label, conversations[0].id])).toEqual([
      ["Today", "today"],
      ["Yesterday", "yesterday"],
      ["Earlier", "older"],
    ])
  })

  it("rejects malformed persisted data and exports readable text", () => {
    expect(parseStoredConversations("not-json")).toEqual([])
    expect(parseStoredConversations(JSON.stringify([{ title: "missing fields" }]))).toEqual([])

    const conversation = createConversation(new Date("2026-07-13T08:00:00.000Z"), "export")
    conversation.title = "Tokyo plan"
    conversation.messages.push({
      id: "request",
      role: "user",
      content: "Plan Tokyo",
      createdAt: "2026-07-13T08:01:00.000Z",
    })

    expect(exportConversation(conversation)).toContain("TripWeaver - Tokyo plan")
    expect(exportConversation(conversation)).toContain("You: Plan Tokyo")
  })
})
