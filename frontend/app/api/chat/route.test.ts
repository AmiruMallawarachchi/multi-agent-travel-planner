import { describe, expect, it, vi } from "vitest"

import { POST } from "./route"

describe("POST /api/chat", () => {
  it("forwards the request body and streams the backend response", async () => {
    const upstream = 'data: {"type":"done"}\n\n'
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(upstream, {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        }),
      ),
    )
    const request = new Request("http://localhost/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "Plan Tokyo" }),
    })

    const response = await POST(request)

    expect(response.status).toBe(200)
    expect(response.headers.get("content-type")).toBe("text/event-stream")
    expect(await response.text()).toBe(upstream)
    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8000/chat/stream",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ message: "Plan Tokyo" }),
        cache: "no-store",
      }),
    )
  })
})
