import { NextResponse } from "next/server"

import {
  backendHeaders,
  backendUrl,
  setAccountToken,
} from "@/app/api/_tripweaver-backend"
import { readJsonObject } from "@/lib/http-response"
import { createClient } from "@/lib/server"

function redirect(request: Request, path: string) {
  return NextResponse.redirect(new URL(path, request.url))
}

export async function GET(request: Request) {
  const code = new URL(request.url).searchParams.get("code")
  if (!code) return redirect(request, "/?auth_error=google")

  const supabase = await createClient()
  const { data, error } = await supabase.auth.exchangeCodeForSession(code)
  if (error || !data.session?.access_token) {
    return redirect(request, "/?auth_error=google")
  }

  const response = await fetch(backendUrl("/auth/oauth"), {
    method: "POST",
    headers: backendHeaders(),
    body: JSON.stringify({ access_token: data.session.access_token }),
    cache: "no-store",
  })
  const body = await readJsonObject(response)
  if (!response.ok || typeof body.token !== "string") {
    await supabase.auth.signOut({ scope: "local" })
    return redirect(request, "/?auth_error=google")
  }

  await setAccountToken(body.token)
  return redirect(request, "/?auth=google")
}
