import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { QuickReplyQuestion } from "./quick-reply-question"

describe("QuickReplyQuestion", () => {
  it("submits a predefined answer", async () => {
    const user = userEvent.setup()
    const onAnswer = vi.fn()
    render(
      <QuickReplyQuestion
        options={[{ id: "two", label: "2 people", value: "2 travellers" }]}
        onAnswer={onAnswer}
      />,
    )

    await user.click(screen.getByRole("button", { name: "2 people" }))
    expect(onAnswer).toHaveBeenCalledWith("2 travellers")
  })

  it("validates and submits a custom answer with Enter", async () => {
    const user = userEvent.setup()
    const onAnswer = vi.fn()
    render(
      <QuickReplyQuestion
        options={[{ id: "one", label: "1 person", value: "1 traveller" }]}
        allowCustomAnswer
        onAnswer={onAnswer}
      />,
    )

    await user.click(screen.getByRole("button", { name: "Something else" }))
    const input = screen.getByRole("textbox", { name: "Custom answer" })
    await user.type(input, "6 travellers{Enter}")
    expect(onAnswer).toHaveBeenCalledWith("6 travellers")
  })

  it("shows and disables the selected answer", () => {
    render(
      <QuickReplyQuestion
        options={[{ id: "slow", label: "Relaxed", value: "relaxed pace" }]}
        answeredValue="relaxed pace"
        onAnswer={() => undefined}
      />,
    )

    expect(screen.getByRole("button", { name: "Relaxed" })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Relaxed" })).toHaveAttribute("aria-pressed", "true")
  })

  it("renders choices as numbered decision rows", () => {
    render(
      <QuickReplyQuestion
        options={[
          { id: "relaxed", label: "Relaxed", value: "relaxed" },
          { id: "balanced", label: "Balanced", value: "balanced" },
        ]}
        onAnswer={() => undefined}
      />,
    )

    expect(screen.getByRole("group", { name: "Answer choices" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Relaxed" })).toHaveTextContent("1Relaxed")
    expect(screen.getByRole("button", { name: "Balanced" })).toHaveTextContent("2Balanced")
  })

  it("shows guided-question progress", () => {
    render(
      <QuickReplyQuestion
        options={[{ id: "all", label: "Complete trip", value: "all expenses" }]}
        step={2}
        totalSteps={3}
        onAnswer={() => undefined}
      />,
    )

    expect(screen.getByText("Question 2 of 3")).toBeInTheDocument()
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "2")
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuemax", "3")
  })
})
