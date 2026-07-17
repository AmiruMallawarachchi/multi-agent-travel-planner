"use client"

import { Save, Trash2, Workflow } from "lucide-react"

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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import type { TripWeaverSettings } from "@/features/tripweaver/types"

interface SettingsDialogProps {
  open: boolean
  settings: TripWeaverSettings
  onOpenChange: (open: boolean) => void
  onSettingsChange: (settings: TripWeaverSettings) => void
  historyCount: number
  onClearHistory: () => void
}

export function SettingsDialog({
  open,
  settings,
  onOpenChange,
  onSettingsChange,
  historyCount,
  onClearHistory,
}: SettingsDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md rounded-[20px]" showCloseButton={false}>
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription>Control how this browser stores and presents your trips.</DialogDescription>
        </DialogHeader>

        <div className="glass-control divide-y divide-border/60 overflow-hidden rounded-2xl">
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

        </div>

        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase text-muted-foreground">Danger zone</p>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="outline"
                className="h-11 w-full justify-between text-destructive hover:bg-destructive/10 hover:text-destructive"
                disabled={historyCount === 0}
              >
                Delete all history
                <Trash2 aria-hidden="true" />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete all conversation history?</AlertDialogTitle>
                <AlertDialogDescription>
                  This permanently removes all {historyCount} saved conversations. This action cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction variant="destructive" onClick={onClearHistory}>
                  Delete all
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>

        <DialogFooter>
          <DialogClose asChild>
            <Button className="h-11 rounded-xl" aria-label="Close settings">Done</Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
