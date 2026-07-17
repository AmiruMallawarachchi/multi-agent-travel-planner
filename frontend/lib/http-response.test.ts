import { describe, expect, it } from "vitest"

import { readJsonObject, responseDetail } from "./http-response"

describe("HTTP response helpers", () => {
  it("returns an empty object for an empty or malformed response", async () => {
    await expect(readJsonObject(new Response(""))).resolves.toEqual({})
    await expect(readJsonObject(new Response("not-json"))).resolves.toEqual({})
  })

  it("preserves a safe backend detail and otherwise uses the fallback", async () => {
    const body = await readJsonObject(Response.json({ detail: "Email already exists" }))
    expect(responseDetail(body, "Unavailable")).toBe("Email already exists")
    expect(responseDetail({}, "Unavailable")).toBe("Unavailable")
  })
})
