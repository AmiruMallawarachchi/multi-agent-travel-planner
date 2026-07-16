import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import {
  mascotMoodForMessage,
  type MascotMood,
  TripWeaverMascot,
} from "./tripweaver-mascot"
import type { ChatMessage } from "@/features/tripweaver/types"

function message(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: "message-1",
    role: "assistant",
    content: "Ready when you are.",
    createdAt: "2026-07-16T08:00:00.000Z",
    ...overrides,
  }
}

describe("TripWeaverMascot", () => {
  it.each<[MascotMood, string, string]>([
    ["hello", "TripWeaver waving hello", "kimi_hello_wave.gif"],
    ["calm", "TripWeaver ready to help", "kimi_idle_calm.gif"],
    ["question", "TripWeaver asking a question", "kimi_question.gif"],
    ["success", "TripWeaver celebrating your answer", "kimi_success.gif"],
    ["thinking", "TripWeaver thinking", "kimi_thinking.gif"],
  ])("renders the %s animation", (mood, accessibleName, filename) => {
    render(<TripWeaverMascot mood={mood} />)

    expect(screen.getByRole("img", { name: accessibleName })).toHaveAttribute(
      "src",
      expect.stringContaining(filename),
    )
  })

  it("derives animation state from the assistant message lifecycle", () => {
    expect(mascotMoodForMessage(message({ id: "trip-welcome" }))).toBe("hello")
    expect(mascotMoodForMessage(message({ content: "" }))).toBe("thinking")
    expect(
      mascotMoodForMessage(
        message({ quickReplies: { options: [{ id: "one", label: "One", value: "one" }] } }),
      ),
    ).toBe("question")
    expect(
      mascotMoodForMessage(
        message({
          quickReplies: {
            options: [{ id: "one", label: "One", value: "one" }],
            answeredValue: "one",
          },
        }),
      ),
    ).toBe("success")
    expect(mascotMoodForMessage(message())).toBe("calm")
  })
})
