"use client"

import Image from "next/image"
import { CircleHelp, Clock3, LogIn, LogOut, Settings2, UserPlus } from "lucide-react"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { AuthMode } from "@/components/tripweaver/auth-dialog"
import type { AccountUser } from "@/features/tripweaver/types"

interface AppHeaderProps {
  account: AccountUser | null
  backendOnline: boolean
  onOpenAuth: (mode: AuthMode) => void
  onOpenHelp: () => void
  onOpenHistory: () => void
  onOpenSettings: () => void
  onSignOut: () => void
}

function initials(account: AccountUser | null) {
  if (!account) return "U"
  return account.name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || account.email[0]?.toUpperCase() || "U"
}

export function AppHeader({
  account,
  backendOnline,
  onOpenAuth,
  onOpenHelp,
  onOpenHistory,
  onOpenSettings,
  onSignOut,
}: AppHeaderProps) {
  return (
    <header className="glass-panel glass-divider relative z-30 grid h-16 grid-cols-[minmax(0,1fr)_auto] items-center rounded-[18px] px-2 sm:h-[70px] sm:px-3 md:grid-cols-[270px_minmax(0,1fr)_auto]">
      <div className="flex min-w-0 items-center gap-2 sm:gap-3">
        <div className="glass-control flex size-11 shrink-0 items-center justify-center overflow-hidden rounded-2xl">
          <Image
            src="/brand/tripweaver-mark.jpg"
            alt=""
            width={44}
            height={44}
            priority
            className="brand-art size-10 object-contain"
          />
        </div>
        <span className="truncate text-base font-semibold text-foreground sm:text-lg">
          TripWeaver
        </span>
      </div>

      <div className="hidden min-w-0 items-center justify-center gap-3 md:flex">
        <p className="truncate text-sm font-semibold text-foreground/90">AI Trip Planning Assistant</p>
        <Badge
          variant="outline"
          className="glass-control h-7 rounded-full px-2.5 font-normal text-muted-foreground"
        >
          <span
            className={`size-1.5 rounded-full ${backendOnline ? "bg-emerald-600" : "bg-rose-500"}`}
            aria-hidden="true"
          />
          {backendOnline ? "Backend online" : "Backend offline"}
        </Badge>
      </div>

      <nav className="flex items-center justify-end gap-1" aria-label="Application">
        <Button
          variant="ghost"
          size="icon"
          className="glass-interactive size-11 rounded-xl hover:bg-accent/60"
          onClick={onOpenHistory}
          aria-label="History"
        >
          <Clock3 aria-hidden="true" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="glass-interactive hidden size-11 rounded-xl hover:bg-accent/60 sm:inline-flex"
          onClick={onOpenSettings}
          aria-label="Settings"
        >
          <Settings2 aria-hidden="true" />
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              className="glass-interactive h-11 gap-2 rounded-xl px-1.5 hover:bg-accent/60 sm:px-2"
              aria-label="User menu"
            >
              <Avatar size="sm">
                <AvatarFallback className="glass-control text-accent-foreground">
                  {initials(account)}
                </AvatarFallback>
              </Avatar>
              <span className="hidden xl:inline">{account ? account.name : "User"}</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <span className="block truncate text-sm font-medium">
                {account ? account.name : "Traveller"}
              </span>
              <span className="block truncate text-xs font-normal text-muted-foreground">
                {account ? account.email : "Guest profile"}
              </span>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            {!account ? (
              <>
                <DropdownMenuItem onSelect={() => onOpenAuth("login")}>
                  <LogIn />
                  Sign in
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={() => onOpenAuth("register")}>
                  <UserPlus />
                  Create account
                </DropdownMenuItem>
                <DropdownMenuSeparator />
              </>
            ) : null}
            <DropdownMenuItem onSelect={onOpenSettings}>
              <Settings2 />
              Settings
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={onOpenHelp}>
              <CircleHelp />
              Help centre
            </DropdownMenuItem>
            {account ? (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={onSignOut}>
                  <LogOut />
                  Sign out
                </DropdownMenuItem>
              </>
            ) : null}
          </DropdownMenuContent>
        </DropdownMenu>
      </nav>
    </header>
  )
}
