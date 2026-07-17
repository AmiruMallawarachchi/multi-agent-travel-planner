import { NextResponse } from "next/server"

import {
  ACCOUNT_BACKEND_UNREACHABLE,
  backendHeaders,
  backendUrl,
  setAccountToken,
} from "@/app/api/_tripweaver-backend"
import { readJsonObject, responseDetail } from "@/lib/http-response"
import { createClient } from "@/lib/server"

function redirect(request: Request, path: string) {
  return NextResponse.redirect(new URL(path, request.url))
}

function redirectAuthError(request: Request, error: string) {
  return redirect(request, `/?auth_error=${encodeURIComponent(error)}`)
}

function oauthErrorCode(status: number, detail: string) {
  if (detail.toLowerCase().includes("google sign-in is not configured")) {
    return "google_not_configured"
  }
  if (status === 401 || status === 403) {
    return "account_backend_rejected"
  }
  if (status >= 500) {
    return "account_backend_unavailable"
  }
  return "account_backend_rejected"
}

export async function GET(request: Request) {
  const code = new URL(request.url).searchParams.get("code")
  if (!code) return redirectAuthError(request, "missing_google_code")

  const supabase = await createClient()
  const { data, error } = await supabase.auth.exchangeCodeForSession(code)
  if (error || !data.session?.access_token) {
    return redirectAuthError(request, "supabase_session_failed")
  }

  let response: Response
  try {
    response = await fetch(backendUrl("/auth/oauth"), {
      method: "POST",
      headers: backendHeaders(),
      body: JSON.stringify({ access_token: data.session.access_token }),
      cache: "no-store",
    })
  } catch {
    await supabase.auth.signOut({ scope: "local" })
    return redirectAuthError(request, "account_backend_unreachable")
  }

  const body = await readJsonObject(response)
  if (!response.ok) {
    const detail = responseDetail(body, ACCOUNT_BACKEND_UNREACHABLE)
    await supabase.auth.signOut({ scope: "local" })
    return redirectAuthError(request, oauthErrorCode(response.status, detail))
  }

  if (typeof body.token !== "string") {
    await supabase.auth.signOut({ scope: "local" })
    return redirectAuthError(request, "account_backend_incomplete")
  }

  await setAccountToken(body.token)
  return redirect(request, "/?auth=google")
}
