import { NextResponse } from "next/server"

import { backendHeaders, backendUrl, setAccountToken } from "../../_tripweaver-backend"
import { readJsonObject, responseDetail } from "@/lib/http-response"

export async function POST(request: Request) {
  const response = await fetch(backendUrl("/auth/register"), {
    method: "POST",
    headers: backendHeaders(),
    body: await request.text(),
  })
  const body = await readJsonObject(response)

  if (!response.ok) {
    return NextResponse.json(
      { detail: responseDetail(body, "The account service is temporarily unavailable") },
      { status: response.status },
    )
  }

  if (typeof body.token !== "string" || !body.user) {
    return NextResponse.json(
      { detail: "The account service returned an incomplete response" },
      { status: 502 },
    )
  }

  await setAccountToken(body.token)
  return NextResponse.json({ user: body.user })
}

