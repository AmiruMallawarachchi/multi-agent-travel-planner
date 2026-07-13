const BACKEND_URL = (process.env.BACKEND_URL ?? "http://localhost:8000").replace(/\/$/, "")

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3_000),
    })

    return Response.json({
      online: true,
      backend: response.ok ? "online" : "offline",
      service: "tripweaver-frontend",
    })
  } catch {
    return Response.json({
      online: true,
      backend: "offline",
      service: "tripweaver-frontend",
    })
  }
}
