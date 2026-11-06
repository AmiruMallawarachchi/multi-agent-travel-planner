import { NextResponse } from "next/server"

import { backendHeaders, backendUrl } from "../_tripweaver-backend"

export async function POST(request: Request) {
  const body = await request.text()

  let upstream: Response
  try {
    upstream = await fetch(backendUrl("/chat/stream"), {
      method: "POST",
      headers: {
        ...backendHeaders(),
        Accept: "text/event-stream",
      },
      body,
      cache: "no-store",
      signal: request.signal,
    })
  } catch {
    // The client shows describeFailure()'s `detail`; an unhandled rejection
    // here would surface as Next's HTML 500 page instead.
    return NextResponse.json(
      {
        detail:
          "The TripWeaver backend is not reachable right now. It may be waking up - try again in a moment.",
      },
      { status: 503 },
    )
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
    },
  })
}
