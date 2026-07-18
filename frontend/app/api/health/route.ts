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
  const [readinessResult, livenessResult] = await Promise.allSettled([
    fetch(`${BACKEND_URL}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5_000),
    }),
    fetch(`${BACKEND_URL}/health/live`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5_000),
    }),
  ])

  const readiness = readinessResult.status === "fulfilled" ? readinessResult.value : null
  const liveness = livenessResult.status === "fulfilled" ? livenessResult.value : null
  let payload: { mcp_servers?: unknown } = {}

  if (readiness?.ok) {
    try {
      payload = (await readiness.json()) as { mcp_servers?: unknown }
    } catch {
      payload = {}
    }
  }

  return Response.json({
    online: true,
    backend: readiness?.ok || liveness?.ok ? "online" : "offline",
    service: "tripweaver-frontend",
    mcp_servers: normalizeMcpServers(payload.mcp_servers),
  })
}
