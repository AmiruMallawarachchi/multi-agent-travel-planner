"use client"

import { FormEvent, useEffect, useState } from "react"
import { Eye, EyeOff, LoaderCircle, LogIn, UserPlus } from "lucide-react"

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

type PasswordStrength = {
  label: "Weak" | "Fair" | "Good" | "Strong"
  level: number
  color: string
}

function passwordStrength(password: string): PasswordStrength | null {
  if (!password) return null
  const checks = [
    password.length >= 8,
    password.length >= 12,
    /[a-z]/.test(password) && /[A-Z]/.test(password),
    /\d/.test(password),
    /[^A-Za-z0-9]/.test(password),
  ].filter(Boolean).length

  if (checks <= 1) return { label: "Weak", level: 1, color: "bg-rose-500" }
  if (checks === 2) return { label: "Fair", level: 2, color: "bg-amber-500" }
  if (checks === 3) return { label: "Good", level: 3, color: "bg-sky-500" }
  return { label: "Strong", level: 4, color: "bg-emerald-500" }
}

interface AuthDialogProps {
  mode: AuthMode | null
  externalError?: string | null
  onModeChange: (mode: AuthMode | null) => void
  onGoogleSignIn: () => Promise<void>
  onSubmit: (mode: AuthMode, payload: { email: string; password: string; name?: string }) => Promise<void>
}

export function AuthDialog({
  mode,
  externalError = null,
  onModeChange,
  onGoogleSignIn,
  onSubmit,
}: AuthDialogProps) {
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [googleSubmitting, setGoogleSubmitting] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const isRegister = mode === "register"
  const strength = isRegister ? passwordStrength(password) : null
  const visibleError = error ?? externalError

  useEffect(() => {
    if (!mode) {
      setError(null)
      setSubmitting(false)
      setGoogleSubmitting(false)
      setPassword("")
      setShowPassword(false)
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

  async function signInWithGoogle() {
    if (googleSubmitting || submitting) return
    setError(null)
    setGoogleSubmitting(true)
    try {
      await onGoogleSignIn()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not start Google sign in")
      setGoogleSubmitting(false)
    }
  }

  return (
    <Dialog open={Boolean(mode)} onOpenChange={(open) => !open && onModeChange(null)}>
      <DialogContent className="w-[calc(100%-2rem)] max-w-md rounded-[20px] p-6 sm:p-7">
        <DialogHeader>
          <DialogTitle>{isRegister ? "Create your account" : "Sign in"}</DialogTitle>
          <DialogDescription>
            Save TripWeaver conversations to your account and continue planning from this browser.
          </DialogDescription>
        </DialogHeader>

        <Button
          type="button"
          variant="outline"
          className="glass-control glass-interactive h-12 w-full rounded-xl text-sm font-semibold"
          disabled={googleSubmitting || submitting}
          onClick={() => void signInWithGoogle()}
        >
          {googleSubmitting ? (
            <LoaderCircle className="animate-spin" aria-hidden="true" />
          ) : (
            <span
              className="flex size-6 items-center justify-center rounded-full bg-white text-sm font-bold text-[#4285f4] shadow-sm"
              aria-hidden="true"
            >
              G
            </span>
          )}
          Continue with Google
        </Button>

        <div className="flex items-center gap-3 text-xs text-muted-foreground" aria-hidden="true">
          <span className="h-px flex-1 bg-border" />
          or continue with email
          <span className="h-px flex-1 bg-border" />
        </div>

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
            <div className="relative">
              <Input
                required
                type={showPassword ? "text" : "password"}
                autoComplete={isRegister ? "new-password" : "current-password"}
                minLength={isRegister ? 8 : 1}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder={isRegister ? "At least 8 characters" : "Your password"}
                className="glass-control h-11 rounded-xl pr-11"
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="absolute right-1 top-1 size-9 rounded-lg"
                aria-label={showPassword ? "Hide password" : "Show password"}
                aria-pressed={showPassword}
                onClick={() => setShowPassword((visible) => !visible)}
              >
                {showPassword ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
              </Button>
            </div>
            {strength ? (
              <div className="space-y-1.5" aria-live="polite">
                <div className="grid grid-cols-4 gap-1" aria-hidden="true">
                  {[1, 2, 3, 4].map((level) => (
                    <span
                      key={level}
                      className={`h-1.5 rounded-full ${level <= strength.level ? strength.color : "bg-muted"}`}
                    />
                  ))}
                </div>
                <div className="flex items-center justify-between gap-3 text-xs">
                  <span className="font-medium text-foreground">{strength.label} password</span>
                  <span className="text-right text-muted-foreground">
                    Use 12+ characters, mixed case, a number, and a symbol
                  </span>
                </div>
              </div>
            ) : null}
          </label>

          {visibleError ? <p className="text-sm text-destructive">{visibleError}</p> : null}

          <Button
            className="h-11 w-full rounded-xl"
            type="submit"
            disabled={submitting || googleSubmitting}
          >
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

