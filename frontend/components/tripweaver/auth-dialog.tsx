"use client"

import { FormEvent, useEffect, useState } from "react"
import { LoaderCircle, LogIn, UserPlus } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"

export type AuthMode = "login" | "register"

interface AuthDialogProps {
  mode: AuthMode | null
  onModeChange: (mode: AuthMode | null) => void
  onSubmit: (mode: AuthMode, payload: { email: string; password: string; name?: string }) => Promise<void>
}

export function AuthDialog({ mode, onModeChange, onSubmit }: AuthDialogProps) {
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const isRegister = mode === "register"

  useEffect(() => {
    if (!mode) {
      setError(null)
      setSubmitting(false)
      setPassword("")
    }
  }, [mode])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!mode || submitting) return
    setError(null)
    setSubmitting(true)
    try {
      await onSubmit(mode, {
        email,
        password,
        name: isRegister ? name : undefined,
      })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not complete sign in")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={Boolean(mode)} onOpenChange={(open) => !open && onModeChange(null)}>
      <DialogContent className="max-w-sm rounded-[20px]">
        <DialogHeader>
          <DialogTitle>{isRegister ? "Create your account" : "Sign in"}</DialogTitle>
          <DialogDescription>
            Save TripWeaver conversations to your account and continue planning from this browser.
          </DialogDescription>
        </DialogHeader>

        <form className="space-y-4" onSubmit={submit}>
          {isRegister ? (
            <label className="block space-y-1.5">
              <span className="text-xs font-medium text-muted-foreground">Name</span>
              <Input
                autoComplete="name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Traveller"
                className="glass-control h-11 rounded-xl"
              />
            </label>
          ) : null}

          <label className="block space-y-1.5">
            <span className="text-xs font-medium text-muted-foreground">Email</span>
            <Input
              required
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              className="glass-control h-11 rounded-xl"
            />
          </label>

          <label className="block space-y-1.5">
            <span className="text-xs font-medium text-muted-foreground">Password</span>
            <Input
              required
              type="password"
              autoComplete={isRegister ? "new-password" : "current-password"}
              minLength={isRegister ? 8 : 1}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={isRegister ? "At least 8 characters" : "Your password"}
              className="glass-control h-11 rounded-xl"
            />
          </label>

          {error ? <p className="text-sm text-destructive">{error}</p> : null}

          <Button className="h-11 w-full rounded-xl" type="submit" disabled={submitting}>
            {submitting ? (
              <LoaderCircle className="animate-spin" aria-hidden="true" />
            ) : isRegister ? (
              <UserPlus aria-hidden="true" />
            ) : (
              <LogIn aria-hidden="true" />
            )}
            {isRegister ? "Create account" : "Sign in"}
          </Button>
        </form>

        <Button
          type="button"
          variant="ghost"
          className="glass-interactive h-11 w-full rounded-xl"
          onClick={() => onModeChange(isRegister ? "login" : "register")}
        >
          {isRegister ? "I already have an account" : "Create a new account"}
        </Button>
      </DialogContent>
    </Dialog>
  )
}

