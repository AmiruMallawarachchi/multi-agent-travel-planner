import { describe, expect, it } from "vitest"

import { describeFailure } from "./chat-errors"

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  })
}

describe("chat request failures", () => {
  it("prefers the backend's own reason over anything inferred from the status", async () => {
    // An oversized attachment used to surface as "check the backend and API
    // credentials", sending people to look at infrastructure for a problem
    // with their file.
    const message = await describeFailure(
      jsonResponse(422, { detail: "Message exceeds 16000 characters" }),
    )

    expect(message).toBe("Message exceeds 16000 characters")
  })

  it("explains a rejected message by what the traveller can change", async () => {
    const message = await describeFailure(new Response("", { status: 422 }))

    expect(message).toMatch(/too long|shorter|attachment/i)
    expect(message).not.toMatch(/credential/i)
  })

  it("separates rate limiting, auth, and backend faults", async () => {
    expect(await describeFailure(new Response("", { status: 429 }))).toMatch(
      /wait|quickly/i,
    )
    expect(await describeFailure(new Response("", { status: 401 }))).toMatch(
      /authenticate/i,
    )
    expect(await describeFailure(new Response("", { status: 503 }))).toMatch(
      /backend/i,
    )
  })
})
