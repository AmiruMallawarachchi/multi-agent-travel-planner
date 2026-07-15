import { NextResponse } from "next/server"

import { accountToken, backendHeaders, backendUrl } from "../_tripweaver-backend"

export async function GET() {
  const token = await accountToken()
  if (!token) {
    return NextResponse.json({ conversations: [] }, { status: 401 })
  }

  const response = await fetch(backendUrl("/conversations"), {
    method: "GET",
    headers: backendHeaders(token),
    cache: "no-store",
  })
  const body = await response.json()
  return NextResponse.json(body, { status: response.status })
}

export async function PUT(request: Request) {
  const token = await accountToken()
  if (!token) {
    return NextResponse.json({ detail: "Not signed in" }, { status: 401 })
  }
  const body = await request.json()
  const id = body?.conversation?.id
  if (!id) {
    return NextResponse.json({ detail: "Conversation id is required" }, { status: 422 })
  }

  const response = await fetch(backendUrl(`/conversations/${encodeURIComponent(id)}`), {
    method: "PUT",
    headers: backendHeaders(token),
    body: JSON.stringify(body),
  })
  const payload = await response.json()
  return NextResponse.json(payload, { status: response.status })
}

export async function DELETE() {
  const token = await accountToken()
  if (!token) {
    return NextResponse.json({ ok: true })
  }

  const response = await fetch(backendUrl("/conversations"), {
    method: "DELETE",
    headers: backendHeaders(token),
  })
  const body = await response.json()
  return NextResponse.json(body, { status: response.status })
}

