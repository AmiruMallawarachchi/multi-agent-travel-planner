"use client"

import { FormEvent, useEffect, useRef, useState } from "react"
import {
  ArrowUp,
  Check,
  CircleX,
  Copy,
  Download,
  FileText,
  LoaderCircle,
  Mic,
  Paperclip,
  Share2,
  Sparkles,
  Square,
  UserRound,
  X,
} from "lucide-react"
import { toast } from "sonner"

import { Markdown } from "@/components/prompt-kit/markdown"
import { QuickReplyQuestion } from "@/components/tripweaver/quick-reply-question"
import {
  mascotMoodForMessage,
  TripWeaverMascot,
} from "@/components/tripweaver/tripweaver-mascot"
import {
  ItineraryDetails,
  StructuredResultPreview,
  itineraryDestination,
} from "@/components/tripweaver/structured-results"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
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
import { Textarea } from "@/components/ui/textarea"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import {
  exportConversation,
  formatConversationTime,
} from "@/features/tripweaver/conversations"
import type {
  Attachment,
  ChatMessage,
  Conversation,
  RuntimeState,
  StructuredResult,
  ToolActivity,
} from "@/features/tripweaver/types"
import { cn } from "@/lib/utils"

interface ChatWorkspaceProps {
  attachments: Attachment[]
  conversation: Conversation
  input: string
  isListening: boolean
  isStreaming: boolean
  runtime: RuntimeState
  showToolActivity: boolean
  onAttachments: (files: FileList | null) => void
  onInputChange: (input: string) => void
  onQuickReply: (messageId: string, value: string) => void
  onRemoveAttachment: (attachmentId: string) => void
  onSend: (message?: string) => void
  onStartVoice: () => void
  onStop: () => void
}

function statusLabel(status: ToolActivity["status"]) {
  if (status === "running") return "Searching..."
  return status.charAt(0).toUpperCase() + status.slice(1)
}

function ToolActivityPanel({ tools }: { tools: ToolActivity[] }) {
  return (
    <div className="glass-divider mb-2 overflow-hidden border-l-2 border-primary/45 bg-accent/15 text-card-foreground">
      <div className="glass-divider flex h-9 items-center gap-2 border-b px-3 text-xs font-semibold">
        <Sparkles className="size-3.5 text-primary" aria-hidden="true" />
        Tool activity
      </div>
      <div className="divide-y divide-border/60 px-3">
        {tools.map((tool) => (
          <div
            key={tool.id}
            className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 py-1.5 text-xs"
          >
            <span className="min-w-0">
              <span className="block truncate font-medium">{tool.label}</span>
              <span className="block truncate text-muted-foreground">{tool.server}</span>
            </span>
            <span className="flex items-center gap-1.5 text-muted-foreground">
              {tool.status === "running" ? (
                <LoaderCircle className="size-3.5 animate-spin text-sky-600" aria-hidden="true" />
              ) : tool.status === "completed" ? (
                <Check className="size-3.5 text-emerald-700" aria-hidden="true" />
              ) : (
                <CircleX className="size-3.5 text-rose-600" aria-hidden="true" />
              )}
              {statusLabel(tool.status)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function looksLikeItinerary(content: string) {
  return /\bday\s+\d+\b/i.test(content) || /\bdaily itinerary\b/i.test(content)
}

function MessageBubble({
  message,
  showToolActivity,
  onOpenItinerary,
  onQuickReply,
  quickRepliesDisabled,
}: {
  message: ChatMessage
  showToolActivity: boolean
  onOpenItinerary: (message: ChatMessage, result?: StructuredResult) => void
  onQuickReply: (messageId: string, value: string) => void
  quickRepliesDisabled: boolean
}) {
  const isUser = message.role === "user"
  const itineraryResult = message.results?.find((result) => result.type === "itinerary")

  async function copyMessage() {
    try {
      await navigator.clipboard.writeText(message.content)
      toast.success("Response copied")
    } catch {
      toast.error("Could not copy this response")
    }
  }

  return (
    <article className={cn("flex items-start gap-2.5", isUser && "flex-row-reverse")}>
      {isUser ? (
        <div
          className="glass-control mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full"
          aria-hidden="true"
        >
          <UserRound className="size-3.5" />
        </div>
      ) : (
        <TripWeaverMascot
          mood={mascotMoodForMessage(message)}
          priority={message.id.endsWith("-welcome")}
          className="mt-0.5 size-11 sm:size-12"
        />
      )}

      <div
        className={cn(
          "min-w-0 max-w-[min(760px,calc(100%-3.5rem))]",
          isUser && "max-w-[min(620px,82%)]",
        )}
      >
        {showToolActivity && message.tools?.length ? <ToolActivityPanel tools={message.tools} /> : null}
        <div
          className={cn(
            "tw-chat-surface rounded-xl px-3.5 py-3 text-sm leading-[1.6] sm:px-4",
            isUser
              ? "border-primary/20 bg-secondary/80 text-secondary-foreground"
              : "text-card-foreground",
          )}
        >
          {message.content ? (
            <Markdown>{message.content}</Markdown>
          ) : (
            <span className="inline-flex items-center gap-2 text-muted-foreground">
              <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
              Planning your trip...
            </span>
          )}

          {!isUser && message.results?.length
            ? message.results.map((result, index) => (
                <StructuredResultPreview
                  key={`${result.tool}-${result.type}-${index}`}
                  result={result}
                />
              ))
            : null}

          {!isUser && message.quickReplies?.options.length ? (
            <QuickReplyQuestion
              options={message.quickReplies.options}
              allowCustomAnswer={message.quickReplies.allowCustomAnswer}
              answeredValue={message.quickReplies.answeredValue}
              disabled={quickRepliesDisabled}
              onAnswer={(value) => onQuickReply(message.id, value)}
            />
          ) : null}

          {message.attachments?.length ? (
            <div className="glass-divider mt-3 flex flex-wrap gap-2 border-t pt-3">
              {message.attachments.map((attachment) => (
                <span
                  key={attachment.id}
                  className="glass-control inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-muted-foreground"
                >
                  <FileText className="size-3.5" aria-hidden="true" />
                  {attachment.name}
                </span>
              ))}
            </div>
          ) : null}

          {!isUser && message.content ? (
            <div className="glass-divider mt-3 flex items-center gap-1 border-t pt-2">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    type="button"
                    size="icon-sm"
                    variant="ghost"
                    onClick={() => void copyMessage()}
                    aria-label="Copy response"
                  >
                    <Copy aria-hidden="true" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Copy response</TooltipContent>
              </Tooltip>
              {itineraryResult || looksLikeItinerary(message.content) ? (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="glass-control glass-interactive ml-1 rounded-xl"
                  onClick={() => onOpenItinerary(message, itineraryResult)}
                >
                  <FileText aria-hidden="true" />
                  View full itinerary
                </Button>
              ) : null}
              <time className="ml-auto text-[11px] text-muted-foreground">
                {formatConversationTime(message.createdAt)}
              </time>
            </div>
          ) : null}
        </div>
      </div>
    </article>
  )
}

function ConversationExport({ conversation }: { conversation: Conversation }) {
  const transcript = exportConversation(conversation)

  async function copyTranscript() {
    try {
      await navigator.clipboard.writeText(transcript)
      toast.success("Conversation copied")
    } catch {
      toast.error("Could not copy the conversation")
    }
  }

  function downloadTranscript() {
    const url = URL.createObjectURL(new Blob([transcript], { type: "text/plain;charset=utf-8" }))
    const anchor = document.createElement("a")
    anchor.href = url
    anchor.download = `${conversation.title.toLocaleLowerCase().replace(/[^a-z0-9]+/g, "-") || "trip"}.txt`
    anchor.click()
    URL.revokeObjectURL(url)
    toast.success("Conversation exported")
  }

  async function shareTranscript() {
    if (!navigator.share) {
      await copyTranscript()
      return
    }
    try {
      await navigator.share({ title: conversation.title, text: transcript })
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        toast.error("Could not share the conversation")
      }
    }
  }

  return (
    <DropdownMenu>
      <Tooltip>
        <TooltipTrigger asChild>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="icon"
              className="glass-control glass-interactive size-10 rounded-lg"
              aria-label="Export or share conversation"
            >
              <Share2 aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
        </TooltipTrigger>
        <TooltipContent>Export or share</TooltipContent>
      </Tooltip>
      <DropdownMenuContent align="end" className="w-52">
        <DropdownMenuItem onSelect={() => void shareTranscript()}>
          <Share2 />
          Share conversation
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => void copyTranscript()}>
          <Copy />
          Copy as text
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={downloadTranscript}>
          <Download />
          Download .txt
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export function ChatWorkspace({
  attachments,
  conversation,
  input,
  isListening,
  isStreaming,
  runtime,
  showToolActivity,
  onAttachments,
  onInputChange,
  onQuickReply,
  onRemoveAttachment,
  onSend,
  onStartVoice,
  onStop,
}: ChatWorkspaceProps) {
  const [itinerarySelection, setItinerarySelection] = useState<{
    message: ChatMessage
    result?: StructuredResult
  } | null>(null)
  const messagesRef = useRef<HTMLDivElement | null>(null)
  const shouldFollowRef = useRef(true)

  useEffect(() => {
    const messages = messagesRef.current
    if (!messages || !shouldFollowRef.current) return
    messages.scrollTo?.({
      top: messages.scrollHeight,
      behavior: isStreaming ? "smooth" : "auto",
    })
  }, [conversation.messages, isStreaming])

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSend()
  }

  return (
    <section className="tw-conversation-canvas grid min-h-0 min-w-0 grid-rows-[50px_minmax(0,1fr)_auto] overflow-hidden rounded-xl">
      <header className="glass-divider flex min-w-0 items-center gap-3 border-b px-3 sm:px-4">
        <div className="min-w-0">
          <p className="text-[11px] font-medium uppercase text-muted-foreground">Conversation</p>
          <h1 className="truncate text-sm font-semibold">{conversation.title}</h1>
        </div>
        <span className="ml-auto hidden truncate text-xs text-muted-foreground lg:block">
          {runtime.activity}
        </span>
        <ConversationExport conversation={conversation} />
      </header>

      <div
        ref={messagesRef}
        className="min-h-0 overscroll-contain overflow-y-auto px-2.5 py-3 sm:px-4 md:px-5"
        aria-live="polite"
        onScroll={(event) => {
          const target = event.currentTarget
          shouldFollowRef.current = target.scrollHeight - target.scrollTop - target.clientHeight < 96
        }}
      >
        <div className="mx-auto flex w-full max-w-[900px] flex-col gap-3.5">
          {conversation.messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              showToolActivity={showToolActivity}
              onOpenItinerary={(selectedMessage, result) =>
                setItinerarySelection({ message: selectedMessage, result })
              }
              onQuickReply={onQuickReply}
              quickRepliesDisabled={isStreaming}
            />
          ))}
          <div aria-hidden="true" />
        </div>
      </div>

      <div className="glass-divider border-t bg-transparent px-2.5 pb-[max(0.4rem,env(safe-area-inset-bottom))] pt-2 sm:px-4">
        <form className="mx-auto w-full max-w-[900px]" onSubmit={submit}>
          {attachments.length > 0 ? (
            <div className="mb-2 flex flex-wrap gap-2">
              {attachments.map((attachment) => (
                <span
                  key={attachment.id}
                  className="glass-control inline-flex h-8 items-center gap-1.5 rounded-lg pl-2 pr-1 text-xs"
                >
                  <FileText className="size-3.5 text-muted-foreground" aria-hidden="true" />
                  {attachment.name}
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-xs"
                    onClick={() => onRemoveAttachment(attachment.id)}
                    aria-label={`Remove ${attachment.name}`}
                  >
                    <X aria-hidden="true" />
                  </Button>
                </span>
              ))}
            </div>
          ) : null}

          <div className="tw-chat-surface rounded-xl p-1.5 focus-within:border-ring focus-within:ring-2 focus-within:ring-ring/25">
            <div className="grid grid-cols-[44px_minmax(0,1fr)] items-start gap-1 sm:grid-cols-[48px_minmax(0,1fr)] sm:gap-1.5">
              <TripWeaverMascot
                mood={isStreaming ? "thinking" : "calm"}
                className="size-11 sm:size-12"
              />
              <div className="min-w-0">
                <Textarea
                  aria-label="Message TripWeaver"
                  placeholder="Type your message..."
                  className="max-h-32 min-h-11 resize-none border-0 bg-transparent px-2 py-1.5 text-sm shadow-none focus-visible:ring-0 dark:bg-transparent"
                  disabled={isStreaming}
                  value={input}
                  onChange={(event) => onInputChange(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault()
                      onSend()
                    }
                  }}
                />
                <div className="flex items-center gap-1">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="glass-interactive size-11 rounded-xl"
                        aria-label="Attach file"
                        asChild
                      >
                        <label>
                          <Paperclip aria-hidden="true" />
                          <input
                            className="sr-only"
                            type="file"
                            accept=".txt,.md,.csv,.json,text/plain,text/markdown,text/csv,application/json"
                            aria-label="Attach a text file"
                            onChange={(event) => {
                              onAttachments(event.target.files)
                              event.target.value = ""
                            }}
                          />
                        </label>
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Attach a text file</TooltipContent>
                  </Tooltip>

                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className={cn(
                          "glass-interactive size-11 rounded-xl",
                          isListening && "bg-rose-500/15 text-rose-600 dark:text-rose-300",
                        )}
                        onClick={onStartVoice}
                        aria-label="Voice input"
                      >
                        <Mic aria-hidden="true" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>{isListening ? "Listening" : "Voice input"}</TooltipContent>
                  </Tooltip>

                  <span className="ml-1 hidden text-xs text-muted-foreground sm:inline">
                    {isListening ? "Listening..." : runtime.activity}
                  </span>

                  <Button
                    type={isStreaming ? "button" : "submit"}
                    size="icon-lg"
                    className="glass-interactive ml-auto size-10 rounded-full bg-primary text-primary-foreground shadow-lg hover:bg-primary/90"
                    disabled={!isStreaming && !input.trim() && attachments.length === 0}
                    aria-label={isStreaming ? "Stop generating" : "Send message"}
                    onClick={isStreaming ? onStop : undefined}
                  >
                    {isStreaming ? (
                      <Square className="size-3.5 fill-current" aria-hidden="true" />
                    ) : (
                      <ArrowUp aria-hidden="true" />
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </form>
        <p className="mt-1 text-center text-[10px] font-medium text-slate-800/95 drop-shadow-[0_1px_1px_rgba(255,255,255,0.7)] dark:text-slate-200/90 dark:drop-shadow-[0_1px_1px_rgba(0,0,0,0.75)] sm:text-[11px]">
          Travel availability and prices can change. Verify important details before booking.
        </p>
      </div>

      <Dialog
        open={Boolean(itinerarySelection)}
        onOpenChange={(open) => !open && setItinerarySelection(null)}
      >
        <DialogContent className="max-h-[85vh] max-w-2xl overflow-y-auto rounded-[20px]">
          <DialogHeader>
            <DialogTitle>
              {itinerarySelection?.result
                ? `${itineraryDestination(itinerarySelection.result.data)} itinerary`
                : "Full itinerary"}
            </DialogTitle>
            <DialogDescription>{conversation.title}</DialogDescription>
          </DialogHeader>
          {itinerarySelection?.result ? (
            <ItineraryDetails data={itinerarySelection.result.data} />
          ) : itinerarySelection?.message ? (
            <Markdown>{itinerarySelection.message.content}</Markdown>
          ) : null}
        </DialogContent>
      </Dialog>
    </section>
  )
}
