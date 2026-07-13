"use client"

import { CircleHelp, Clock3, LogOut, Settings2, Waypoints } from "lucide-react"

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

interface AppHeaderProps {
  backendOnline: boolean
  onOpenHistory: () => void
  onOpenSettings: () => void
}

export function AppHeader({ backendOnline, onOpenHistory, onOpenSettings }: AppHeaderProps) {
  return (
    <header className="grid h-[68px] grid-cols-[minmax(0,1fr)_auto] items-center border-b bg-background px-3 md:grid-cols-[248px_minmax(0,1fr)_auto] md:px-0">
      <div className="flex min-w-0 items-center gap-3 md:px-4">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-[#153e3a] text-white shadow-sm">
          <Waypoints className="size-[18px]" aria-hidden="true" />
        </div>
        <span className="truncate text-base font-semibold">TripWeaver</span>
      </div>

      <div className="hidden min-w-0 items-center justify-center gap-3 md:flex">
        <p className="truncate text-sm font-semibold">AI Trip Planning Assistant</p>
        <Badge
          variant="outline"
          className="h-6 rounded-full px-2 font-normal text-muted-foreground"
        >
          <span
            className={`size-1.5 rounded-full ${backendOnline ? "bg-emerald-600" : "bg-rose-500"}`}
            aria-hidden="true"
          />
          {backendOnline ? "Backend online" : "Backend offline"}
        </Badge>
      </div>

      <nav className="flex items-center justify-end gap-0.5 pr-0 md:pr-3" aria-label="Application">
        <Button
          variant="ghost"
          className="h-9 px-2.5"
          onClick={onOpenHistory}
          aria-label="History"
        >
          <Clock3 aria-hidden="true" />
          <span className="hidden lg:inline">History</span>
        </Button>
        <Button
          variant="ghost"
          className="h-9 px-2.5"
          onClick={onOpenSettings}
          aria-label="Settings"
        >
          <Settings2 aria-hidden="true" />
          <span className="hidden lg:inline">Settings</span>
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-10 gap-2 px-2" aria-label="User menu">
              <Avatar size="sm">
                <AvatarFallback className="bg-[#e8f1ef] text-[#153e3a]">U</AvatarFallback>
              </Avatar>
              <span className="hidden lg:inline">User</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-52">
            <DropdownMenuLabel>
              <span className="block text-sm font-medium">Traveller</span>
              <span className="block text-xs font-normal text-muted-foreground">Local profile</span>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={onOpenSettings}>
              <Settings2 />
              Settings
            </DropdownMenuItem>
            <DropdownMenuItem disabled>
              <CircleHelp />
              Help centre
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem disabled>
              <LogOut />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </nav>
    </header>
  )
}
