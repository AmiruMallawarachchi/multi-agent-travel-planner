"use client"

import { Moon, Save, Workflow } from "lucide-react"
import { useTheme } from "next-themes"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Switch } from "@/components/ui/switch"
import type { TripWeaverSettings } from "@/features/tripweaver/types"

interface SettingsDialogProps {
  open: boolean
  settings: TripWeaverSettings
  onOpenChange: (open: boolean) => void
  onSettingsChange: (settings: TripWeaverSettings) => void
}

export function SettingsDialog({
  open,
  settings,
  onOpenChange,
  onSettingsChange,
}: SettingsDialogProps) {
  const { resolvedTheme, setTheme } = useTheme()

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md rounded-lg" showCloseButton={false}>
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription>Control how this browser stores and presents your trips.</DialogDescription>
        </DialogHeader>

        <div className="divide-y rounded-md border">
          <label className="grid grid-cols-[32px_minmax(0,1fr)_auto] items-center gap-3 p-3">
            <Save className="size-4 text-muted-foreground" aria-hidden="true" />
            <span>
              <span className="block text-sm font-medium">Save conversation history</span>
              <span className="block text-xs text-muted-foreground">Store chats in this browser</span>
            </span>
            <Switch
              aria-label="Save conversation history"
              checked={settings.autoSave}
              onCheckedChange={(autoSave) => onSettingsChange({ ...settings, autoSave })}
            />
          </label>

          <label className="grid grid-cols-[32px_minmax(0,1fr)_auto] items-center gap-3 p-3">
            <Workflow className="size-4 text-muted-foreground" aria-hidden="true" />
            <span>
              <span className="block text-sm font-medium">Show tool activity</span>
              <span className="block text-xs text-muted-foreground">Display MCP progress in chat</span>
            </span>
            <Switch
              aria-label="Show tool activity"
              checked={settings.showToolActivity}
              onCheckedChange={(showToolActivity) =>
                onSettingsChange({ ...settings, showToolActivity })
              }
            />
          </label>

          <label className="grid grid-cols-[32px_minmax(0,1fr)_auto] items-center gap-3 p-3">
            <Moon className="size-4 text-muted-foreground" aria-hidden="true" />
            <span>
              <span className="block text-sm font-medium">Dark appearance</span>
              <span className="block text-xs text-muted-foreground">Use a darker workspace</span>
            </span>
            <Switch
              aria-label="Dark appearance"
              checked={resolvedTheme === "dark"}
              onCheckedChange={(checked) => setTheme(checked ? "dark" : "light")}
            />
          </label>
        </div>

        <DialogFooter>
          <DialogClose asChild>
            <Button aria-label="Close settings">Done</Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
