import { NextResponse } from "next/server"

import { accountToken, backendHeaders, backendUrl } from "../../_tripweaver-backend"

export async function GET() {
  const token = await accountToken()
  if (!token) {
    return NextResponse.json({ detail: "Not signed in" }, { status: 401 })
  }

  const response = await fetch(backendUrl("/auth/me"), {
    method: "GET",
    headers: backendHeaders(token),
    cache: "no-store",
  })
  const body = await response.json()
  return NextResponse.json(body, { status: response.status })
}

