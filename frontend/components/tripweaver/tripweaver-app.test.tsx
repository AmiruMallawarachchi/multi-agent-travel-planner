import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { AppProviders } from "@/components/app-providers"

import { TripWeaverApp } from "./tripweaver-app"

function sseResponse(frames: string[]) {
  const encoder = new TextEncoder()
  return new Response(
    new ReadableStream({
      start(controller) {
        frames.forEach((frame) => controller.enqueue(encoder.encode(`data: ${frame}\n\n`)))
        controller.close()
      },
    }),
    { status: 200, headers: { "Content-Type": "text/event-stream" } },
  )
}

function renderApp() {
  return render(
    <AppProviders>
      <TripWeaverApp />
    </AppProviders>,
  )
}

describe("TripWeaverApp", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        if (String(input).includes("/api/health")) {
          return Response.json({
            online: true,
            backend: "online",
            mcp_servers: {
              "hotel-mcp": "available",
              "flight-mcp": "available",
              "itinerary-mcp": "available",
              "weather-mcp": "available",
              "currency-mcp": "available",
              "location-mcp": "available",
            },
          })
        }
        return sseResponse([
          '{"type":"session","session_id":"session-1"}',
          '{"type":"tool","status":"INVOKED","tool":"search_flights"}',
          '{"type":"tool","status":"SUCCEEDED","tool":"search_flights"}',
          '{"type":"token","content":"I found two flight options."}',
          '{"type":"done"}',
        ])
      }),
    )
  })

  it("renders the requested travel workspace", async () => {
    const { container } = renderApp()

    expect(screen.getByText("TripWeaver")).toBeInTheDocument()
    expect(container.querySelector(".tw-app-background")).toBeInTheDocument()
    expect(container.querySelector(".tw-conversation-canvas")).toBeInTheDocument()
    expect(container.querySelector('img[src*="tripweaver-mark"]')).toBeInTheDocument()
    expect(container.querySelector('img[src*="tripweaver-wordmark"]')).not.toBeInTheDocument()
    expect(screen.getByText("AI Trip Planning Assistant")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "SOL" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "LUNA" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Toggle conversation history" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "All chats" })).toBeInTheDocument()
    expect(screen.getByText("Plans")).toBeInTheDocument()
    expect(screen.getByRole("img", { name: "TripWeaver waving hello" })).toBeInTheDocument()
    expect(screen.getByRole("img", { name: "TripWeaver ready to help" })).toBeInTheDocument()
    expect(screen.getByText("TripWeaver").tagName).toBe("SPAN")
    expect(screen.getByRole("button", { name: "Export or share conversation" })).toHaveTextContent(/^$/)
    expect(screen.getByText("Active tools & status")).toBeInTheDocument()
    expect(screen.getByText("Trip context")).toBeInTheDocument()
    expect(screen.queryByText("Quick actions")).not.toBeInTheDocument()
    expect(screen.getByRole("complementary", { name: "Trip status" })).toHaveClass(
      "overflow-y-auto",
    )
    expect(
      screen.getByText(
        "Travel availability and prices can change. Verify important details before booking.",
      ),
    ).toHaveClass("text-slate-800/95", "dark:text-slate-200/90")
    await waitFor(() => expect(screen.getByText("Backend online")).toBeInTheDocument())
  })

  it("persists the selected appearance and exposes responsive panels", async () => {
    const user = userEvent.setup()
    renderApp()

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "SOL" })).toHaveAttribute(
        "aria-pressed",
        "true",
      )
      expect(screen.getByRole("button", { name: "LUNA" })).toHaveAttribute(
        "aria-pressed",
        "false",
      )
    })

    await user.click(screen.getByRole("button", { name: "LUNA" }))

    await waitFor(() => {
      expect(document.documentElement).toHaveClass("dark")
      expect(window.localStorage.getItem("tripweaver.theme")).toBe("dark")
      expect(screen.getByRole("button", { name: "SOL" })).toHaveAttribute(
        "aria-pressed",
        "false",
      )
      expect(screen.getByRole("button", { name: "LUNA" })).toHaveAttribute(
        "aria-pressed",
        "true",
      )
    })

    await user.click(screen.getByRole("button", { name: "Toggle trip tools" }))
    expect(screen.queryByText("Active tools & status")).not.toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Toggle trip tools" }))
    expect(screen.getByText("Active tools & status")).toBeInTheDocument()

    expect(screen.getByText("Plans")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Toggle conversation history" }))
    expect(screen.queryByText("Plans")).not.toBeInTheDocument()
    expect(window.localStorage.getItem("tripweaver.sidebars.v1")).toContain('"history":false')
    await user.click(screen.getByRole("button", { name: "Toggle conversation history" }))
    expect(screen.getByText("Plans")).toBeInTheDocument()
  })

  it("opens history and tools as modal drawers on compact screens", async () => {
    vi.stubGlobal(
      "matchMedia",
      vi.fn((query: string) => ({
        matches: query.includes("max-width"),
        media: query,
        onchange: null,
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
        addListener: () => undefined,
        removeListener: () => undefined,
        dispatchEvent: () => false,
      })),
    )
    const user = userEvent.setup()
    renderApp()

    await user.click(screen.getByRole("button", { name: "Toggle conversation history" }))
    expect(screen.getByRole("dialog", { name: "Conversation history" })).toBeInTheDocument()
    await user.keyboard("{Escape}")

    await user.click(screen.getByRole("button", { name: "Toggle trip tools" }))
    expect(screen.getByRole("dialog", { name: "Trip status" })).toBeInTheDocument()
  })

  it("submits a structured quick reply once", async () => {
    const user = userEvent.setup()
    renderApp()

    await user.click(screen.getByRole("button", { name: "Flights" }))

    expect(
      screen.getByRole("img", { name: "TripWeaver celebrating your answer" }),
    ).toBeInTheDocument()
    expect(await screen.findByText("I found two flight options.")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Flights" })).toBeDisabled()
    expect(fetch).toHaveBeenCalledWith(
      "/api/chat",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining("Help me search for flights."),
      }),
    )
  })

  it("supports settings, attachments, search, and individual history actions", async () => {
    const user = userEvent.setup()
    renderApp()

    await user.click(screen.getByRole("button", { name: "Settings" }))
    expect(screen.getByRole("dialog", { name: "Settings" })).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Close settings" }))

    const attachment = new File(["Window seat preferred"], "preferences.txt", {
      type: "text/plain",
    })
    const fileInput = screen.getByLabelText("Attach a text file")
    fireEvent.change(fileInput, { target: { files: [attachment] } })
    expect(await screen.findByText("preferences.txt")).toBeInTheDocument()

    await user.type(screen.getByRole("textbox", { name: "Message TripWeaver" }), "Plan Tokyo")
    await user.click(screen.getByRole("button", { name: "Send message" }))
    await screen.findByText("I found two flight options.")

    await user.type(screen.getByRole("searchbox", { name: "Search conversations" }), "Tokyo")
    expect(screen.getByRole("button", { name: /^Plan Tokyo,/ })).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Actions for Plan Tokyo" }))
    await user.click(screen.getByText("Pin conversation"))
    expect(screen.getByText("Pinned")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Create plan" }))
    await user.type(screen.getByRole("textbox", { name: "Plan name" }), "Japan 2027")
    await user.click(screen.getByRole("button", { name: "Create" }))
    expect(screen.getByRole("button", { name: "Japan 2027, 0 chats" })).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Actions for Plan Tokyo" }))
    await user.click(screen.getByRole("menuitem", { name: "Add to plan" }))
    expect(screen.getByRole("dialog", { name: "Add to plan" })).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: /Japan 2027/ }))
    expect(screen.getByRole("button", { name: "Japan 2027, 1 chat" })).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Actions for Plan Tokyo" }))
    await user.click(screen.getByText("Rename conversation"))
    const nameInput = screen.getByRole("textbox", { name: "Conversation name" })
    await user.clear(nameInput)
    await user.type(nameInput, "Tokyo escape")
    await user.click(screen.getByRole("button", { name: "Rename" }))
    expect(screen.getByRole("button", { name: /^Tokyo escape,/ })).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Actions for Tokyo escape" }))
    await user.click(screen.getByText("Delete conversation"))
    expect(screen.getByRole("alertdialog", { name: /Delete "Tokyo escape"/ })).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Delete" }))
    expect(screen.getByText("No matching conversations")).toBeInTheDocument()
  }, 15_000)

  it("handles unsupported voice input", async () => {
    const user = userEvent.setup()
    renderApp()

    await user.click(screen.getByRole("button", { name: "Voice input" }))
    expect(await screen.findByText("Voice input is not supported by this browser")).toBeInTheDocument()
  })

  it("opens a structured itinerary returned by the backend", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        if (String(input).includes("/api/health")) {
          return Response.json({
            online: true,
            backend: "online",
            mcp_servers: {
              "hotel-mcp": "available",
              "flight-mcp": "available",
              "itinerary-mcp": "available",
              "weather-mcp": "available",
              "currency-mcp": "available",
              "location-mcp": "available",
            },
          })
        }
        return sseResponse([
          '{"type":"session","session_id":"session-1"}',
          '{"type":"tool","status":"INVOKED","tool":"create_itinerary"}',
          '{"type":"result","result_type":"itinerary","tool":"create_itinerary","data":{"destination":"Tokyo","start_date":"2026-12-10","end_date":"2026-12-11","duration_days":2,"travelers":2,"pace":"balanced","days":[{"day_number":1,"date":"2026-12-10","title":"Day 1 in Tokyo","items":[{"name":"Food planning block in Tokyo","time_slot":"morning","duration_minutes":120,"is_placeholder":true}]}],"disclaimer":"Confirm specific venues before relying on this itinerary."}}',
          '{"type":"token","content":"Your itinerary is ready."}',
          '{"type":"done"}',
        ])
      }),
    )
    const user = userEvent.setup()
    renderApp()

    await user.type(
      screen.getByRole("textbox", { name: "Message TripWeaver" }),
      "Plan Tokyo",
    )
    await user.click(screen.getByRole("button", { name: "Send message" }))

    await user.click(
      await screen.findByRole("button", { name: "View full itinerary" }),
    )
    expect(
      screen.getByRole("dialog", { name: "Tokyo itinerary" }),
    ).toBeInTheDocument()
    expect(screen.getByText("Day 1 in Tokyo")).toBeInTheDocument()
    expect(screen.getByText("Food planning block in Tokyo")).toBeInTheDocument()
  })

  it("opens help centre and registers a traveller account", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes("/api/health")) {
          return Response.json({ online: true, backend: "online", mcp_servers: {} })
        }
        if (url.includes("/api/auth/me")) {
          return Response.json({ detail: "Not signed in" }, { status: 401 })
        }
        if (url.includes("/api/auth/register")) {
          return Response.json({
            user: {
              id: "user-1",
              email: "maya@example.com",
              name: "Maya",
              created_at: "2026-07-14T10:00:00+00:00",
            },
          })
        }
        if (url.includes("/api/conversations")) {
          return Response.json({ conversations: [] })
        }
        if (url.includes("/api/plans")) {
          return Response.json({ plans: [] })
        }
        return sseResponse(['{"type":"done"}'])
      }),
    )
    const user = userEvent.setup()
    renderApp()

    await user.click(screen.getByRole("button", { name: "User menu" }))
    await user.click(screen.getByText("Help centre"))
    expect(screen.getByRole("dialog", { name: "Help centre" })).toBeInTheDocument()
    await user.keyboard("{Escape}")

    await user.click(screen.getByRole("button", { name: "User menu" }))
    await user.click(screen.getByText("Create account"))
    await user.type(screen.getByLabelText("Name"), "Maya")
    await user.type(screen.getByLabelText("Email"), "maya@example.com")
    await user.type(screen.getByLabelText("Password"), "correct horse")
    await user.click(screen.getByRole("button", { name: "Create account" }))

    expect(await screen.findByText("Account created")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "User menu" })).toHaveTextContent("Maya")
    await user.click(screen.getByRole("button", { name: "New chat" }))
    expect(screen.getByText(/Welcome, Maya\. Hi, I am TripWeaver\./)).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith(
      "/api/auth/register",
      expect.objectContaining({ method: "POST" }),
    )
  })

  it("loads account-backed conversation history for a signed-in traveller", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes("/api/health")) {
          return Response.json({ online: true, backend: "online", mcp_servers: {} })
        }
        if (url.includes("/api/auth/me")) {
          return Response.json({
            id: "user-1",
            email: "maya@example.com",
            name: "Maya",
            created_at: "2026-07-14T10:00:00+00:00",
            avatar_url: "https://lh3.googleusercontent.com/maya.jpg",
          })
        }
        if (url.includes("/api/conversations")) {
          return Response.json({
            conversations: [
              {
                id: "cloud-trip",
                title: "Cloud Tokyo",
                sessionId: "0123456789abcdef0123456789abcdef",
                createdAt: "2026-07-14T10:00:00.000Z",
                updatedAt: "2026-07-14T10:01:00.000Z",
                tripContext: {
                  destination: "Tokyo",
                  dates: null,
                  travelers: null,
                  budget: null,
                  preferences: [],
                },
                messages: [
                  {
                    id: "m1",
                    role: "user",
                    content: "Plan Tokyo",
                    createdAt: "2026-07-14T10:00:00.000Z",
                  },
                ],
              },
            ],
          })
        }
        if (url.includes("/api/plans")) {
          return Response.json({
            plans: [
              {
                id: "japan-plan",
                name: "Japan plans",
                createdAt: "2026-07-14T09:00:00.000Z",
                updatedAt: "2026-07-14T09:00:00.000Z",
              },
            ],
          })
        }
        return sseResponse(['{"type":"done"}'])
      }),
    )

    renderApp()

    expect(await screen.findByRole("button", { name: "User menu" })).toHaveTextContent("Maya")
    expect(screen.getAllByAltText("Maya profile photo")).toHaveLength(2)
    expect(screen.getByRole("button", { name: /^Cloud Tokyo,/ })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Japan plans, 0 chats" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "User menu" })).toHaveTextContent("Maya")
  })
})
