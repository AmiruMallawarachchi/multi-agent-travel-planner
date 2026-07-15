import { NextResponse } from "next/server"

import {
  accountToken,
  backendHeaders,
  backendUrl,
  clearAccountToken,
} from "../../_tripweaver-backend"

export async function POST() {
  const token = await accountToken()
  if (token) {
    await fetch(backendUrl("/auth/logout"), {
      method: "POST",
      headers: backendHeaders(token),
    })
  }
  await clearAccountToken()
  return NextResponse.json({ ok: true })
}

