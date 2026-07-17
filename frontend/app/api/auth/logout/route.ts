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
    try {
      await fetch(backendUrl("/auth/logout"), {
        method: "POST",
        headers: backendHeaders(token),
      })
    } catch {
      // Clear the browser session even if the demo backend is asleep or restarting.
    }
  }
  await clearAccountToken()
  return NextResponse.json({ ok: true })
}

