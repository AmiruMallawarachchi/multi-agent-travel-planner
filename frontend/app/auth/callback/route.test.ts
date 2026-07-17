import { beforeEach, describe, expect, it, vi } from "vitest"

const mocks = vi.hoisted(() => ({
  exchangeCodeForSession: vi.fn(),
  signOut: vi.fn(),
  setAccountToken: vi.fn(),
}))

vi.mock("@/lib/server", () => ({
  createClient: vi.fn(async () => ({
    auth: {
      exchangeCodeForSession: mocks.exchangeCodeForSession,
      signOut: mocks.signOut,
    },
  })),
}))

vi.mock("@/app/api/_tripweaver-backend", () => ({
  backendHeaders: () => ({ "Content-Type": "application/json" }),
  backendUrl: (path: string) => `https://backend.test${path}`,
  setAccountToken: mocks.setAccountToken,
}))

import { GET } from "./route"

describe("Google auth callback", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("exchanges the Supabase session for a TripWeaver account cookie", async () => {
    mocks.exchangeCodeForSession.mockResolvedValue({
      data: { session: { access_token: "supabase-access-token" } },
      error: null,
    })
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Response.json({ token: "tripweaver-token", user: { id: "u1" } })),
    )

    const response = await GET(new Request("https://app.test/auth/callback?code=oauth-code"))

    expect(mocks.exchangeCodeForSession).toHaveBeenCalledWith("oauth-code")
    expect(fetch).toHaveBeenCalledWith(
      "https://backend.test/auth/oauth",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ access_token: "supabase-access-token" }),
      }),
    )
    expect(mocks.setAccountToken).toHaveBeenCalledWith("tripweaver-token")
    expect(response.headers.get("location")).toBe("https://app.test/?auth=google")
  })

  it("redirects safely when Supabase does not return a session", async () => {
    mocks.exchangeCodeForSession.mockResolvedValue({ data: { session: null }, error: null })

    const response = await GET(new Request("https://app.test/auth/callback?code=oauth-code"))

    expect(response.headers.get("location")).toBe("https://app.test/?auth_error=google")
    expect(mocks.setAccountToken).not.toHaveBeenCalled()
  })
})
