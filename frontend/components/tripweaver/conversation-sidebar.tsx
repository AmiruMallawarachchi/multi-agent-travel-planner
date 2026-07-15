"use client"

import { MessageSquare, Plus, Search, Trash2 } from "lucide-react"

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
import { Button } from "@/components/ui/button"
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
  onClear: () => void
  onNewChat: () => void
  onQueryChange: (query: string) => void
  onSelect: (conversationId: string) => void
  className?: string
}

export function ConversationSidebar({
  activeConversationId,
  conversations,
  query,
  onClear,
  onNewChat,
  onQueryChange,
  onSelect,
  className,
}: ConversationSidebarProps) {
  const history = conversations.filter(hasUserMessage)
  const filtered = searchConversations(history, query)
  const groups = groupConversations(filtered)

  return (
    <div className={cn("flex h-full min-h-0 flex-col text-sidebar-foreground", className)}>
      <div className="glass-divider space-y-3 border-b p-3.5">
        <Button
          variant="outline"
          className="glass-control glass-interactive h-11 w-full justify-center rounded-xl font-semibold"
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
            className="glass-control h-11 rounded-xl pl-9 shadow-none"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
          />
        </label>
      </div>

      <div className="px-4 pb-2 pt-5">
        <h2 className="text-xs font-semibold uppercase text-muted-foreground">Recent chats</h2>
      </div>

      <ScrollArea className="min-h-0 flex-1 px-2.5">
        {groups.length > 0 ? (
          <div className="space-y-4 pb-4">
            {groups.map((group) => (
              <section key={group.label} aria-labelledby={`history-${group.label}`}>
                <h3
                  id={`history-${group.label}`}
                  className="mb-1 px-2 text-xs text-muted-foreground"
                >
                  {group.label}
                </h3>
                <div className="space-y-0.5">
                  {group.conversations.map((conversation) => (
                    <button
                      key={conversation.id}
                      type="button"
                      aria-label={`${conversation.title}, ${formatConversationTime(conversation.updatedAt)}`}
                      aria-current={conversation.id === activeConversationId ? "page" : undefined}
                      onClick={() => onSelect(conversation.id)}
                      className={cn(
                        "glass-interactive grid min-h-12 w-full grid-cols-[18px_minmax(0,1fr)] items-start gap-2 rounded-xl border border-transparent px-2.5 py-2.5 text-left hover:border-sidebar-border hover:bg-sidebar-accent/75 hover:text-sidebar-accent-foreground",
                        conversation.id === activeConversationId &&
                          "border-sidebar-border bg-sidebar-accent/80 text-sidebar-accent-foreground shadow-sm hover:bg-sidebar-accent/80",
                      )}
                    >
                      <MessageSquare className="mt-0.5 size-4 text-muted-foreground" aria-hidden="true" />
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium">{conversation.title}</span>
                        <span className="block text-xs text-muted-foreground">
                          {formatConversationTime(conversation.updatedAt)}
                        </span>
                      </span>
                    </button>
                  ))}
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

      <div className="glass-divider border-t p-3">
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="ghost"
              className="glass-interactive h-11 w-full justify-between rounded-xl px-2.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
              aria-label="Clear conversations"
              disabled={history.length === 0}
            >
              Clear conversations
              <Trash2 aria-hidden="true" />
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Clear all conversations?</AlertDialogTitle>
              <AlertDialogDescription>
                This removes the chat history stored in this browser. This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction variant="destructive" onClick={onClear}>
                Clear all
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  )
}
