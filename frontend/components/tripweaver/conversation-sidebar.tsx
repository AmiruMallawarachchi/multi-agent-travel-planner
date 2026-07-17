"use client"

import { useState } from "react"
import {
  Check,
  Folder,
  FolderOpen,
  FolderPlus,
  MessageSquare,
  MessagesSquare,
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
import type { Conversation, PlanFolder } from "@/features/tripweaver/types"
import { cn } from "@/lib/utils"

interface ConversationSidebarProps {
  activeConversationId: string
  conversations: Conversation[]
  plans: PlanFolder[]
  query: string
  onAssignPlan: (conversationId: string, planId?: string) => void
  onCreatePlan: (name: string) => void
  onDelete: (conversationId: string) => void
  onDeletePlan: (planId: string) => void
  onNewChat: () => void
  onPin: (conversationId: string, pinned: boolean) => void
  onQueryChange: (query: string) => void
  onRename: (conversationId: string, title: string) => void
  onRenamePlan: (planId: string, name: string) => void
  onSelect: (conversationId: string) => void
  className?: string
}

export function ConversationSidebar({
  activeConversationId,
  conversations,
  plans,
  query,
  onAssignPlan,
  onCreatePlan,
  onDelete,
  onDeletePlan,
  onNewChat,
  onPin,
  onQueryChange,
  onRename,
  onRenamePlan,
  onSelect,
  className,
}: ConversationSidebarProps) {
  const history = conversations.filter(hasUserMessage)
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null)
  const planHistory = selectedPlanId
    ? history.filter((conversation) => conversation.planId === selectedPlanId)
    : history
  const filtered = searchConversations(planHistory, query)
  const pinned = filtered.filter((conversation) => conversation.pinned)
  const groups = groupConversations(filtered.filter((conversation) => !conversation.pinned))
  const [createPlanOpen, setCreatePlanOpen] = useState(false)
  const [renameTarget, setRenameTarget] = useState<Conversation | null>(null)
  const [assignPlanTarget, setAssignPlanTarget] = useState<Conversation | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Conversation | null>(null)
  const [renamePlanTarget, setRenamePlanTarget] = useState<PlanFolder | null>(null)
  const [deletePlanTarget, setDeletePlanTarget] = useState<PlanFolder | null>(null)
  const [dialogValue, setDialogValue] = useState("")

  function openRename(conversation: Conversation) {
    setRenameTarget(conversation)
    setDialogValue(conversation.title)
  }

  function openRenamePlan(plan: PlanFolder) {
    setRenamePlanTarget(plan)
    setDialogValue(plan.name)
  }

  function assignToPlan(planId?: string) {
    if (!assignPlanTarget) return
    onAssignPlan(assignPlanTarget.id, planId)
    setSelectedPlanId(planId ?? null)
    setAssignPlanTarget(null)
  }

  function submitName() {
    const value = dialogValue.trim()
    if (!value) return
    if (renameTarget) onRename(renameTarget.id, value)
    if (renamePlanTarget) onRenamePlan(renamePlanTarget.id, value)
    if (createPlanOpen) onCreatePlan(value)
    setCreatePlanOpen(false)
    setRenameTarget(null)
    setRenamePlanTarget(null)
    setDialogValue("")
  }

  function historyItem(conversation: Conversation) {
    const isActive = conversation.id === activeConversationId
    return (
      <div
        key={conversation.id}
        className={cn(
          "glass-interactive group grid min-h-11 grid-cols-[minmax(0,1fr)_36px] items-center rounded-md border border-transparent hover:border-sidebar-border hover:bg-sidebar-accent/55",
          isActive && "border-sidebar-border bg-sidebar-accent/70 text-sidebar-accent-foreground",
        )}
      >
        <button
          type="button"
          aria-label={`${conversation.title}, ${formatConversationTime(conversation.updatedAt)}`}
          aria-current={isActive ? "page" : undefined}
          onClick={() => onSelect(conversation.id)}
          className="grid min-w-0 grid-cols-[16px_minmax(0,1fr)] items-center gap-2 rounded-md px-2 py-2 text-left focus-visible:outline-2 focus-visible:outline-ring"
        >
          {conversation.pinned ? (
            <Pin className="size-3.5 text-primary" aria-hidden="true" />
          ) : (
            <MessageSquare className="size-3.5 text-muted-foreground" aria-hidden="true" />
          )}
          <span className="min-w-0">
            <span className="block truncate text-[13px] font-medium">{conversation.title}</span>
            <span className="block truncate text-[11px] text-muted-foreground">
              {conversation.planId
                ? plans.find((plan) => plan.id === conversation.planId)?.name ?? "Plan"
                : formatConversationTime(conversation.updatedAt)}
            </span>
          </span>
        </button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              className="size-8 rounded-md text-muted-foreground opacity-65 hover:bg-background/25 hover:text-foreground focus:opacity-100 group-hover:opacity-100"
              aria-label={`Actions for ${conversation.title}`}
            >
              <MoreHorizontal aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" sideOffset={4} className="w-52">
            <DropdownMenuItem onSelect={() => onPin(conversation.id, !conversation.pinned)}>
              {conversation.pinned ? <PinOff /> : <Pin />}
              {conversation.pinned ? "Unpin conversation" : "Pin conversation"}
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => openRename(conversation)}>
              <Pencil />
              Rename conversation
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => setAssignPlanTarget(conversation)}>
              <Folder />
              Add to plan
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" onSelect={() => setDeleteTarget(conversation)}>
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
      <div className="glass-divider space-y-2 border-b p-3">
        <Button
          variant="outline"
          className="glass-control glass-interactive h-10 w-full justify-center rounded-md font-semibold"
          onClick={onNewChat}
          aria-label="New chat"
        >
          <Plus aria-hidden="true" />
          New chat
        </Button>
        <label className="relative block">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <Input
            id="conversation-search"
            type="search"
            aria-label="Search conversations"
            placeholder="Search chats"
            className="glass-control h-9 rounded-md pl-9 shadow-none"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
          />
        </label>
      </div>

      <ScrollArea className="min-h-0 flex-1">
        <nav className="glass-divider border-b px-2.5 py-3" aria-label="Plans and chats">
          <div className="mb-1 flex h-8 items-center justify-between px-2">
            <h2 className="text-xs font-semibold uppercase text-muted-foreground">Plans</h2>
            <Button
              type="button"
              variant="ghost"
              size="icon-xs"
              className="rounded-md"
              aria-label="Create plan"
              onClick={() => {
                setDialogValue("")
                setCreatePlanOpen(true)
              }}
            >
              <FolderPlus aria-hidden="true" />
            </Button>
          </div>
          <button
            type="button"
            aria-label="All chats"
            className={cn(
              "glass-interactive flex h-9 w-full items-center gap-2 rounded-md px-2 text-left text-sm hover:bg-sidebar-accent/55",
              selectedPlanId === null && "bg-sidebar-accent/65",
            )}
            onClick={() => setSelectedPlanId(null)}
          >
            <MessagesSquare className="size-4" aria-hidden="true" />
            <span className="min-w-0 flex-1 truncate">All chats</span>
            <span className="text-xs text-muted-foreground">{history.length}</span>
          </button>
          {plans.map((plan) => {
            const count = history.filter((conversation) => conversation.planId === plan.id).length
            const selected = selectedPlanId === plan.id
            return (
              <div key={plan.id} className="group grid grid-cols-[minmax(0,1fr)_32px] items-center">
                <button
                  type="button"
                  aria-label={`${plan.name}, ${count} ${count === 1 ? "chat" : "chats"}`}
                  className={cn(
                    "glass-interactive flex h-9 min-w-0 items-center gap-2 rounded-md px-2 text-left text-sm hover:bg-sidebar-accent/55",
                    selected && "bg-sidebar-accent/65",
                  )}
                  onClick={() => setSelectedPlanId(plan.id)}
                >
                  {selected ? <FolderOpen className="size-4" /> : <Folder className="size-4" />}
                  <span className="min-w-0 flex-1 truncate">{plan.name}</span>
                  <span className="text-xs text-muted-foreground">{count}</span>
                </button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-xs"
                      className="rounded-md opacity-55 group-hover:opacity-100"
                      aria-label={`Actions for plan ${plan.name}`}
                    >
                      <MoreHorizontal aria-hidden="true" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-44">
                    <DropdownMenuItem onSelect={() => openRenamePlan(plan)}>
                      <Pencil />
                      Rename plan
                    </DropdownMenuItem>
                    <DropdownMenuItem variant="destructive" onSelect={() => setDeletePlanTarget(plan)}>
                      <Trash2 />
                      Delete plan
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            )
          })}
        </nav>

        <div className="px-2.5 pb-4 pt-3">
          <h2 className="mb-2 px-2 text-xs font-semibold uppercase text-muted-foreground">
            {selectedPlanId ? plans.find((plan) => plan.id === selectedPlanId)?.name : "Chats"}
          </h2>
          {pinned.length > 0 || groups.length > 0 ? (
            <div className="space-y-3">
              {pinned.length > 0 ? (
                <section aria-labelledby="history-pinned">
                  <h3 id="history-pinned" className="mb-1 px-2 text-[11px] text-muted-foreground">Pinned</h3>
                  <div className="space-y-0.5">{pinned.map(historyItem)}</div>
                </section>
              ) : null}
              {groups.map((group) => (
                <section key={group.label} aria-labelledby={`history-${group.label}`}>
                  <h3 id={`history-${group.label}`} className="mb-1 px-2 text-[11px] text-muted-foreground">
                    {group.label}
                  </h3>
                  <div className="space-y-0.5">{group.conversations.map(historyItem)}</div>
                </section>
              ))}
            </div>
          ) : (
            <div className="px-2 py-6 text-center text-sm text-muted-foreground">
              {query ? "No matching conversations" : selectedPlanId ? "No chats in this plan" : "No conversations yet"}
            </div>
          )}
        </div>
      </ScrollArea>

      <Dialog
        open={createPlanOpen || Boolean(renameTarget) || Boolean(renamePlanTarget)}
        onOpenChange={(open) => {
          if (open) return
          setCreatePlanOpen(false)
          setRenameTarget(null)
          setRenamePlanTarget(null)
        }}
      >
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>
              {createPlanOpen ? "Create plan" : renamePlanTarget ? "Rename plan" : "Rename conversation"}
            </DialogTitle>
            <DialogDescription>
              {createPlanOpen
                ? "Group related travel chats so they stay easy to find."
                : "Choose a short, recognizable name."}
            </DialogDescription>
          </DialogHeader>
          <Input
            autoFocus
            aria-label={createPlanOpen || renamePlanTarget ? "Plan name" : "Conversation name"}
            maxLength={80}
            value={dialogValue}
            onChange={(event) => setDialogValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") submitName()
            }}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setCreatePlanOpen(false)
              setRenameTarget(null)
              setRenamePlanTarget(null)
            }}>Cancel</Button>
            <Button disabled={!dialogValue.trim()} onClick={submitName}>
              {createPlanOpen ? "Create" : "Rename"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={Boolean(assignPlanTarget)}
        onOpenChange={(open) => {
          if (!open) setAssignPlanTarget(null)
        }}
      >
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Add to plan</DialogTitle>
            <DialogDescription>
              Choose where to group &quot;{assignPlanTarget?.title}&quot;.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Button
              type="button"
              variant="outline"
              className="glass-control h-10 w-full justify-start gap-2 rounded-md"
              onClick={() => assignToPlan()}
            >
              {!assignPlanTarget?.planId ? <Check aria-hidden="true" /> : <MessagesSquare aria-hidden="true" />}
              All chats
            </Button>
            {plans.length > 0 ? (
              plans.map((plan) => {
                const selected = assignPlanTarget?.planId === plan.id
                const count = history.filter((conversation) => conversation.planId === plan.id).length
                return (
                  <Button
                    key={plan.id}
                    type="button"
                    variant="outline"
                    className="glass-control h-10 w-full justify-start gap-2 rounded-md"
                    onClick={() => assignToPlan(plan.id)}
                  >
                    {selected ? <Check aria-hidden="true" /> : <Folder aria-hidden="true" />}
                    <span className="min-w-0 flex-1 truncate text-left">{plan.name}</span>
                    <span className="text-xs text-muted-foreground">{count}</span>
                  </Button>
                )
              })
            ) : (
              <p className="rounded-md border border-border/60 bg-background/30 px-3 py-2 text-sm text-muted-foreground">
                No plan folders yet.
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAssignPlanTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setAssignPlanTarget(null)
                setDialogValue("")
                setCreatePlanOpen(true)
              }}
            >
              <FolderPlus aria-hidden="true" />
              New plan
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={Boolean(deleteTarget)} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete &quot;{deleteTarget?.title}&quot;?</AlertDialogTitle>
            <AlertDialogDescription>This removes only this conversation. This action cannot be undone.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={() => {
              if (deleteTarget) onDelete(deleteTarget.id)
              setDeleteTarget(null)
            }}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={Boolean(deletePlanTarget)} onOpenChange={(open) => !open && setDeletePlanTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete plan &quot;{deletePlanTarget?.name}&quot;?</AlertDialogTitle>
            <AlertDialogDescription>The chats stay in your history and are removed only from this plan.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={() => {
              if (deletePlanTarget) {
                onDeletePlan(deletePlanTarget.id)
                if (selectedPlanId === deletePlanTarget.id) setSelectedPlanId(null)
              }
              setDeletePlanTarget(null)
            }}>Delete plan</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
