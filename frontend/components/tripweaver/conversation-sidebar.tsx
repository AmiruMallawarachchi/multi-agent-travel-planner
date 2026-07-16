"use client"

import { useState } from "react"
import {
  MessageSquare,
  MoreHorizontal,
  Pencil,
  Pin,
  PinOff,
  Plus,
  Search,
  Trash2,
} from "lucide-react"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  formatConversationTime,
  groupConversations,
  hasUserMessage,
  searchConversations,
} from "@/features/tripweaver/conversations"
import type { Conversation } from "@/features/tripweaver/types"
import { cn } from "@/lib/utils"

interface ConversationSidebarProps {
  activeConversationId: string
  conversations: Conversation[]
  query: string
  onDelete: (conversationId: string) => void
  onNewChat: () => void
  onPin: (conversationId: string, pinned: boolean) => void
  onQueryChange: (query: string) => void
  onRename: (conversationId: string, title: string) => void
  onSelect: (conversationId: string) => void
  className?: string
}

export function ConversationSidebar({
  activeConversationId,
  conversations,
  query,
  onDelete,
  onNewChat,
  onPin,
  onQueryChange,
  onRename,
  onSelect,
  className,
}: ConversationSidebarProps) {
  const history = conversations.filter(hasUserMessage)
  const filtered = searchConversations(history, query)
  const pinned = filtered.filter((conversation) => conversation.pinned)
  const groups = groupConversations(filtered.filter((conversation) => !conversation.pinned))
  const [renameTarget, setRenameTarget] = useState<Conversation | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Conversation | null>(null)
  const [renameValue, setRenameValue] = useState("")

  function openRename(conversation: Conversation) {
    setRenameTarget(conversation)
    setRenameValue(conversation.title)
  }

  function submitRename() {
    const title = renameValue.trim()
    if (!renameTarget || !title) return
    onRename(renameTarget.id, title)
    setRenameTarget(null)
  }

  function historyItem(conversation: Conversation) {
    const isActive = conversation.id === activeConversationId
    return (
      <div
        key={conversation.id}
        className={cn(
          "glass-interactive group grid min-h-12 grid-cols-[minmax(0,1fr)_40px] items-center rounded-lg border border-transparent hover:border-sidebar-border hover:bg-sidebar-accent/70",
          isActive &&
            "border-sidebar-border bg-sidebar-accent/80 text-sidebar-accent-foreground shadow-sm",
        )}
      >
        <button
          type="button"
          aria-label={`${conversation.title}, ${formatConversationTime(conversation.updatedAt)}`}
          aria-current={isActive ? "page" : undefined}
          onClick={() => onSelect(conversation.id)}
          className="grid min-w-0 grid-cols-[18px_minmax(0,1fr)] items-start gap-2 rounded-lg px-2.5 py-2.5 text-left focus-visible:outline-2 focus-visible:outline-ring"
        >
          {conversation.pinned ? (
            <Pin className="mt-0.5 size-4 text-primary" aria-hidden="true" />
          ) : (
            <MessageSquare className="mt-0.5 size-4 text-muted-foreground" aria-hidden="true" />
          )}
          <span className="min-w-0">
            <span className="block truncate text-sm font-medium">{conversation.title}</span>
            <span className="block text-xs text-muted-foreground">
              {formatConversationTime(conversation.updatedAt)}
            </span>
          </span>
        </button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="size-10 rounded-lg text-muted-foreground opacity-70 hover:bg-background/45 hover:text-foreground focus:opacity-100 group-hover:opacity-100"
              aria-label={`Actions for ${conversation.title}`}
            >
              <MoreHorizontal aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" sideOffset={4} className="w-48">
            <DropdownMenuItem onSelect={() => onPin(conversation.id, !conversation.pinned)}>
              {conversation.pinned ? <PinOff /> : <Pin />}
              {conversation.pinned ? "Unpin conversation" : "Pin conversation"}
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => openRename(conversation)}>
              <Pencil />
              Rename conversation
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              variant="destructive"
              onSelect={() => setDeleteTarget(conversation)}
            >
              <Trash2 />
              Delete conversation
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    )
  }

  return (
    <div className={cn("flex h-full min-h-0 flex-col text-sidebar-foreground", className)}>
      <div className="glass-divider space-y-2.5 border-b p-3">
        <Button
          variant="outline"
          className="glass-control glass-interactive h-10 w-full justify-center rounded-lg font-semibold"
          onClick={onNewChat}
          aria-label="New chat"
        >
          <Plus aria-hidden="true" />
          New chat
        </Button>
        <label className="relative block">
          <Search
            className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            id="conversation-search"
            type="search"
            aria-label="Search conversations"
            placeholder="Search conversations"
            className="glass-control h-10 rounded-lg pl-9 shadow-none"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
          />
        </label>
      </div>

      <div className="px-4 pb-2 pt-4">
        <h2 className="text-xs font-semibold uppercase text-muted-foreground">History</h2>
      </div>

      <ScrollArea className="min-h-0 flex-1 px-2.5">
        {pinned.length > 0 || groups.length > 0 ? (
          <div className="space-y-4 pb-4">
            {pinned.length > 0 ? (
              <section aria-labelledby="history-pinned">
                <h3 id="history-pinned" className="mb-1 px-2 text-xs text-muted-foreground">
                  Pinned
                </h3>
                <div className="space-y-0.5">{pinned.map(historyItem)}</div>
              </section>
            ) : null}
            {groups.map((group) => (
              <section key={group.label} aria-labelledby={`history-${group.label}`}>
                <h3
                  id={`history-${group.label}`}
                  className="mb-1 px-2 text-xs text-muted-foreground"
                >
                  {group.label}
                </h3>
                <div className="space-y-0.5">
                  {group.conversations.map(historyItem)}
                </div>
              </section>
            ))}
          </div>
        ) : (
          <div className="px-2 py-8 text-center text-sm text-muted-foreground">
            {query ? "No matching conversations" : "No conversations yet"}
          </div>
        )}
      </ScrollArea>

      <Dialog open={Boolean(renameTarget)} onOpenChange={(open) => !open && setRenameTarget(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Rename conversation</DialogTitle>
            <DialogDescription>Choose a short name that is easy to find later.</DialogDescription>
          </DialogHeader>
          <Input
            autoFocus
            aria-label="Conversation name"
            maxLength={80}
            value={renameValue}
            onChange={(event) => setRenameValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") submitRename()
            }}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setRenameTarget(null)}>Cancel</Button>
            <Button disabled={!renameValue.trim()} onClick={submitRename}>Rename</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={Boolean(deleteTarget)} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete &quot;{deleteTarget?.title}&quot;?</AlertDialogTitle>
            <AlertDialogDescription>
              This removes only this conversation. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={() => {
                if (deleteTarget) onDelete(deleteTarget.id)
                setDeleteTarget(null)
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
