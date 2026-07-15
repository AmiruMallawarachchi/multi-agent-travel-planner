import { NextResponse } from "next/server"

import { backendHeaders, backendUrl, setAccountToken } from "../../_tripweaver-backend"

export async function POST(request: Request) {
  const response = await fetch(backendUrl("/auth/login"), {
    method: "POST",
    headers: backendHeaders(),
    body: await request.text(),
  })
  const body = await response.json()

  if (!response.ok) {
    return NextResponse.json(body, { status: response.status })
  }

  await setAccountToken(body.token)
  return NextResponse.json({ user: body.user })
}

