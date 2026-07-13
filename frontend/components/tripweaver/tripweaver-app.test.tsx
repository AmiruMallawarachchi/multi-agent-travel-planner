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
          return Response.json({ online: true, backend: "online" })
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
    renderApp()

    expect(screen.getByText("TripWeaver")).toBeInTheDocument()
    expect(screen.getByText("AI Trip Planning Assistant")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "New chat" })).toBeInTheDocument()
    expect(screen.getByText("Active tools & status")).toBeInTheDocument()
    expect(screen.getByText("Trip context")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Search flights" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Search hotels" })).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText("Backend online")).toBeInTheDocument())
  })

  it("prefills a supported quick action and streams a real chat response", async () => {
    const user = userEvent.setup()
    renderApp()

    await user.click(screen.getByRole("button", { name: "Search flights" }))
    const composer = screen.getByRole("textbox", { name: "Message TripWeaver" })
    expect(composer).toHaveValue("Help me search for flights.")

    await user.click(screen.getByRole("button", { name: "Send message" }))

    expect(await screen.findByText("I found two flight options.")).toBeInTheDocument()
    expect(screen.getAllByText("Completed").length).toBeGreaterThan(0)
    expect(fetch).toHaveBeenCalledWith(
      "/api/chat",
      expect.objectContaining({ method: "POST" }),
    )
  })

  it("supports settings, attachments, conversation search, and clearing history", async () => {
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
    expect(screen.getByRole("button", { name: /Plan Tokyo/ })).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Clear conversations" }))
    expect(screen.getByRole("alertdialog", { name: "Clear all conversations?" })).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Clear all" }))
    expect(screen.getByText("No conversations yet")).toBeInTheDocument()
  })

  it("identifies unavailable roadmap tools and unsupported voice input", async () => {
    const user = userEvent.setup()
    renderApp()

    await user.click(screen.getByRole("button", { name: "Check weather" }))
    expect(
      await screen.findByText(
        "Weather MCP is not connected yet. Its status is shown as unavailable.",
      ),
    ).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Voice input" }))
    expect(await screen.findByText("Voice input is not supported by this browser")).toBeInTheDocument()
  })
})
