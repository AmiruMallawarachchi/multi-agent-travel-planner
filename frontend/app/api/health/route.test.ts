import { describe, expect, it, vi } from "vitest"

import { GET } from "./route"

describe("GET /api/health", () => {
  it("reports backend availability from the real health check", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input) => {
        if (String(input).endsWith("/health/live")) {
          return Response.json({ status: "ok" })
        }
        return Response.json({
          status: "ok",
          mcp_servers: {
            "hotel-mcp": "available",
            "flight-mcp": "available",
            "itinerary-mcp": "available",
            "weather-mcp": "available",
            "currency-mcp": "available",
            "location-mcp": "unavailable",
          },
        })
      }),
    )

    const response = await GET()

    expect(response.status).toBe(200)
    expect(await response.json()).toEqual({
      online: true,
      backend: "online",
      service: "tripweaver-frontend",
      mcp_servers: {
        "hotel-mcp": "available",
        "flight-mcp": "available",
        "itinerary-mcp": "available",
        "weather-mcp": "available",
        "currency-mcp": "available",
        "location-mcp": "unavailable",
      },
    })
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8000/health",
      expect.objectContaining({ cache: "no-store" }),
    )
    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8000/health/live",
      expect.objectContaining({ cache: "no-store" }),
    )
  })

  it("keeps the backend online while MCP readiness is still warming", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input) => {
        if (String(input).endsWith("/health")) {
          throw new Error("readiness timeout")
        }
        return Response.json({ status: "ok" })
      }),
    )

    const response = await GET()

    expect(await response.json()).toMatchObject({
      online: true,
      backend: "online",
      mcp_servers: {},
    })
  })

  it("stays healthy while accurately reporting an unreachable backend", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new Error("offline"))))

    const response = await GET()

    expect(await response.json()).toMatchObject({
      online: true,
      backend: "offline",
      mcp_servers: {},
    })
  })
})
