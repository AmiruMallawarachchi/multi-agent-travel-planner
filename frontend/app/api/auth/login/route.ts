import { NextResponse } from "next/server"

import {
  ACCOUNT_BACKEND_UNREACHABLE,
  backendHeaders,
  backendUrl,
  setAccountToken,
} from "../../_tripweaver-backend"
import { readJsonObject, responseDetail } from "@/lib/http-response"

export async function POST(request: Request) {
  let response: Response
  try {
    response = await fetch(backendUrl("/auth/login"), {
      method: "POST",
      headers: backendHeaders(),
      body: await request.text(),
    })
  } catch {
    return NextResponse.json({ detail: ACCOUNT_BACKEND_UNREACHABLE }, { status: 503 })
  }

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

