import { cookies } from "next/headers"

export const SESSION_COOKIE = "tripweaver_session"

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000"
const BACKEND_API_KEY = process.env.BACKEND_API_KEY

export function backendUrl(path: string) {
  return `${BACKEND_URL}${path}`
}

export function backendHeaders(token?: string) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  }
  if (BACKEND_API_KEY) {
    headers["X-API-Key"] = BACKEND_API_KEY
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  return headers
}

export async function accountToken() {
  return (await cookies()).get(SESSION_COOKIE)?.value
}

export async function setAccountToken(token: string) {
  ;(await cookies()).set(SESSION_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 30,
  })
}

export async function clearAccountToken() {
  ;(await cookies()).delete(SESSION_COOKIE)
}

