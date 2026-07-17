import { NextResponse } from "next/server"

import { accountToken, backendHeaders, backendUrl } from "../_tripweaver-backend"

export async function GET() {
  const token = await accountToken()
  if (!token) return NextResponse.json({ plans: [] })

  const response = await fetch(backendUrl("/plans"), {
    cache: "no-store",
    headers: backendHeaders(token),
  })
  const payload = await response.json()
  return NextResponse.json(payload, { status: response.status })
}

export async function PUT(request: Request) {
  const token = await accountToken()
  if (!token) return NextResponse.json({ ok: true })

  const body = (await request.json()) as { plan?: { id?: string } }
  const id = body.plan?.id
  if (!id) return NextResponse.json({ detail: "Plan id is required" }, { status: 422 })

  const response = await fetch(backendUrl(`/plans/${encodeURIComponent(id)}`), {
    method: "PUT",
    headers: backendHeaders(token),
    body: JSON.stringify(body),
  })
  const payload = await response.json()
  return NextResponse.json(payload, { status: response.status })
}

export async function DELETE(request: Request) {
  const token = await accountToken()
  if (!token) return NextResponse.json({ ok: true })

  const id = new URL(request.url).searchParams.get("id")
  if (!id) return NextResponse.json({ detail: "Plan id is required" }, { status: 422 })

  const response = await fetch(backendUrl(`/plans/${encodeURIComponent(id)}`), {
    method: "DELETE",
    headers: backendHeaders(token),
  })
  const payload = await response.json()
  return NextResponse.json(payload, { status: response.status })
}
