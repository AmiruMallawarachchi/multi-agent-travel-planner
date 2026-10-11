import { describe, expect, it } from "vitest"

import { composeRequest } from "./compose-request"

const LIMIT = 200

describe("composing a chat request", () => {
  it("sends a plain message untouched", () => {
    expect(composeRequest("hotels in Colombo", [])).toEqual({
      message: "hotels in Colombo",
      trimmed: [],
    })
  })

  it("keeps the whole request inside the budget the backend enforces", () => {
    const { message, trimmed } = composeRequest(
      "use my notes",
      [{ name: "notes.txt", content: "x".repeat(5000) }],
      LIMIT,
    )

    // The old composer sliced at 15000 regardless of the backend cap, so every
    // real attachment came back as a 422.
    expect(message.length).toBeLessThanOrEqual(LIMIT)
    expect(message).toContain('<attachment name="notes.txt">')
    expect(trimmed).toEqual(["notes.txt"])
  })

  it("does not report trimming when the file already fits", () => {
    const { message, trimmed } = composeRequest(
      "use my notes",
      [{ name: "notes.txt", content: "short note" }],
      LIMIT,
    )

    expect(message).toContain("short note")
    expect(trimmed).toEqual([])
  })

  it("never sacrifices the traveller's own words to fit an attachment", () => {
    const content = "y".repeat(LIMIT)

    const { message, trimmed } = composeRequest(
      content,
      [{ name: "huge.txt", content: "x".repeat(5000) }],
      LIMIT,
    )

    expect(message).toBe(content)
    expect(trimmed).toEqual(["huge.txt"])
  })
})
