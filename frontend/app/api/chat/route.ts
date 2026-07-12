import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BACKEND_URL = (process.env.BACKEND_URL || "http://localhost:8000").replace(/\/$/, "");

export async function POST(request: NextRequest) {
  const body = await request.text();
  const headers: HeadersInit = { "Content-Type": "application/json" };
  if (process.env.BACKEND_API_KEY) headers["X-API-Key"] = process.env.BACKEND_API_KEY;

  try {
    const response = await fetch(`${BACKEND_URL}/chat/stream`, {
      method: "POST",
      headers,
      body,
      cache: "no-store",
    });

    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("Content-Type") || "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
      },
    });
  } catch {
    return Response.json(
      { detail: "TripWeaver backend is unavailable." },
      { status: 503 },
    );
  }
}
