const BACKEND_URL = (process.env.BACKEND_URL ?? "http://localhost:8000").replace(/\/$/, "")
const BACKEND_API_KEY = process.env.BACKEND_API_KEY ?? ""

export async function POST(request: Request) {
  const body = await request.text()

  const headers = new Headers({
    "Content-Type": "application/json",
    Accept: "text/event-stream",
  })

  if (BACKEND_API_KEY) {
    headers.set("X-API-Key", BACKEND_API_KEY)
  }

  const upstream = await fetch(`${BACKEND_URL}/chat/stream`, {
    method: "POST",
    headers,
    body,
    cache: "no-store",
  })

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
    },
  })
}
