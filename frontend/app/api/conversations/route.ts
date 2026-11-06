import { NextResponse } from "next/server"

import {
  ACCOUNT_BACKEND_UNREACHABLE,
  accountToken,
  backendHeaders,
  backendUrl,
} from "../_tripweaver-backend"
import { readJsonObject } from "@/lib/http-response"

async function proxyToBackend(
  token: string,
  path: string,
  init: { method?: string; body?: string } = {},
) {
  let response: Response
  try {
    response = await fetch(backendUrl(path), {
      method: init.method ?? "GET",
      headers: backendHeaders(token),
      body: init.body,
      cache: "no-store",
    })
  } catch {
    return NextResponse.json({ detail: ACCOUNT_BACKEND_UNREACHABLE }, { status: 503 })
  }
  // readJsonObject keeps a gateway's HTML error page from throwing here.
  const payload = await readJsonObject(response)
  return NextResponse.json(payload, { status: response.status })
}

export async function GET() {
  const token = await accountToken()
  if (!token) {
    return NextResponse.json({ conversations: [] }, { status: 401 })
  }
  return proxyToBackend(token, "/conversations")
}

export async function PUT(request: Request) {
  const token = await accountToken()
  if (!token) {
    return NextResponse.json({ detail: "Not signed in" }, { status: 401 })
  }
  const body = (await request.json()) as { conversation?: { id?: string } }
  const id = body.conversation?.id
  if (!id) {
    return NextResponse.json({ detail: "Conversation id is required" }, { status: 422 })
  }
  return proxyToBackend(token, `/conversations/${encodeURIComponent(id)}`, {
    method: "PUT",
    body: JSON.stringify(body),
  })
}

export async function DELETE(request: Request) {
  const token = await accountToken()
  if (!token) {
    return NextResponse.json({ ok: true })
  }

  const id = new URL(request.url).searchParams.get("id")
  const path = id ? `/conversations/${encodeURIComponent(id)}` : "/conversations"
  return proxyToBackend(token, path, { method: "DELETE" })
}
