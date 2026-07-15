const BACKEND_URL = (process.env.BACKEND_URL ?? "http://localhost:8000").replace(/\/$/, "")

const MCP_SERVERS = new Set([
  "flight-mcp",
  "hotel-mcp",
  "itinerary-mcp",
  "weather-mcp",
  "currency-mcp",
  "location-mcp",
])

function normalizeMcpServers(value: unknown) {
  if (!value || typeof value !== "object") return {}

  return Object.fromEntries(
    Object.entries(value).filter(
      ([server, status]) =>
        MCP_SERVERS.has(server) && (status === "available" || status === "unavailable"),
    ),
  )
}

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5_000),
    })
    const payload = response.ok ? ((await response.json()) as { mcp_servers?: unknown }) : {}

    return Response.json({
      online: true,
      backend: response.ok ? "online" : "offline",
      service: "tripweaver-frontend",
      mcp_servers: normalizeMcpServers(payload.mcp_servers),
    })
  } catch {
    return Response.json({
      online: true,
      backend: "offline",
      service: "tripweaver-frontend",
      mcp_servers: {},
    })
  }
}
