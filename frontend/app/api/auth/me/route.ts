import { NextResponse } from "next/server"

import { accountToken, backendHeaders, backendUrl } from "../../_tripweaver-backend"
import { readJsonObject, responseDetail } from "@/lib/http-response"

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
  const body = await readJsonObject(response)
  if (!response.ok) {
    return NextResponse.json(
      { detail: responseDetail(body, "The account service is temporarily unavailable") },
      { status: response.status },
    )
  }
  return NextResponse.json(body)
}

