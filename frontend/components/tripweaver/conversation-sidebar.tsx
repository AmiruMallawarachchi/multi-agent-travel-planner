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
    <div className={cn("flex h-full min-h-0 flex-col bg-[#fbfcfc]", className)}>
      <div className="space-y-3 border-b p-3">
        <Button
          variant="outline"
          className="h-10 w-full justify-center bg-background shadow-xs"
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
            className="h-9 bg-background pl-8"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
          />
        </label>
      </div>

      <div className="px-3 pb-2 pt-4">
        <h2 className="text-xs font-semibold uppercase text-muted-foreground">Recent chats</h2>
      </div>

      <ScrollArea className="min-h-0 flex-1 px-2">
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
                        "grid w-full grid-cols-[18px_minmax(0,1fr)] items-start gap-2 rounded-md px-2 py-2 text-left transition-colors hover:bg-muted",
                        conversation.id === activeConversationId && "bg-[#e8f1ef] hover:bg-[#e8f1ef]",
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

      <div className="border-t p-3">
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="ghost"
              className="h-9 w-full justify-between px-2 text-muted-foreground"
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
