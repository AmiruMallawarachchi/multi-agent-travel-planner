import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { AuthDialog } from "./auth-dialog"

describe("AuthDialog", () => {
  it("shows password strength and toggles password visibility", async () => {
    const user = userEvent.setup()
    render(
      <AuthDialog
        mode="register"
        onModeChange={vi.fn()}
        onGoogleSignIn={vi.fn()}
        onSubmit={vi.fn()}
      />,
    )

    const password = screen.getByLabelText("Password")
    expect(password).toHaveAttribute("type", "password")

    await user.type(password, "TripWeaver2026!")
    expect(screen.getByText("Strong password")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Show password" }))
    expect(password).toHaveAttribute("type", "text")
    expect(screen.getByRole("button", { name: "Hide password" })).toHaveAttribute(
      "aria-pressed",
      "true",
    )
  })

  it("labels a short password as weak", async () => {
    const user = userEvent.setup()
    render(
      <AuthDialog
        mode="register"
        onModeChange={vi.fn()}
        onGoogleSignIn={vi.fn()}
        onSubmit={vi.fn()}
      />,
    )

    await user.type(screen.getByLabelText("Password"), "short")
    expect(screen.getByText("Weak password")).toBeInTheDocument()
  })

  it("starts Google sign in from either account mode", async () => {
    const user = userEvent.setup()
    const onGoogleSignIn = vi.fn().mockResolvedValue(undefined)
    render(
      <AuthDialog
        mode="login"
        onModeChange={vi.fn()}
        onGoogleSignIn={onGoogleSignIn}
        onSubmit={vi.fn()}
      />,
    )

    await user.click(screen.getByRole("button", { name: "Continue with Google" }))
    expect(onGoogleSignIn).toHaveBeenCalledOnce()
  })
})
