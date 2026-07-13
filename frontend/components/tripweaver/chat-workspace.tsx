"use client"

import { FormEvent, useEffect, useRef, useState } from "react"
import {
  ArrowUp,
  Bot,
  Check,
  CircleX,
  Copy,
  Download,
  FileText,
  LoaderCircle,
  Mic,
  PanelRight,
  Paperclip,
  Share2,
  Sparkles,
  UserRound,
  X,
} from "lucide-react"
import { toast } from "sonner"

import { Markdown } from "@/components/prompt-kit/markdown"
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
  onOpenStatus: () => void
  onRemoveAttachment: (attachmentId: string) => void
  onSend: (message?: string) => void
  onStartVoice: () => void
}

function statusLabel(status: ToolActivity["status"]) {
  if (status === "running") return "Searching..."
  return status.charAt(0).toUpperCase() + status.slice(1)
}

function ToolActivityPanel({ tools }: { tools: ToolActivity[] }) {
  return (
    <div className="mb-3 overflow-hidden rounded-md border bg-[#fbfcfc]">
      <div className="flex h-9 items-center gap-2 border-b px-3 text-xs font-semibold">
        <Sparkles className="size-3.5 text-[#2f7d72]" aria-hidden="true" />
        Tool activity
      </div>
      <div className="divide-y px-3">
        {tools.map((tool) => (
          <div
            key={tool.id}
            className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 py-2 text-xs"
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
}: {
  message: ChatMessage
  showToolActivity: boolean
  onOpenItinerary: (message: ChatMessage, result?: StructuredResult) => void
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
    <article className={cn("flex items-start gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "mt-1 flex size-8 shrink-0 items-center justify-center rounded-full border bg-background",
          !isUser && "border-[#b8d1cc] bg-[#e8f1ef] text-[#153e3a]",
        )}
        aria-hidden="true"
      >
        {isUser ? <UserRound className="size-4" /> : <Bot className="size-4" />}
      </div>

      <div className={cn("min-w-0 max-w-[720px]", isUser && "max-w-[620px]") }>
        {showToolActivity && message.tools?.length ? <ToolActivityPanel tools={message.tools} /> : null}
        <div
          className={cn(
            "rounded-md border px-4 py-3 text-sm leading-6 shadow-xs",
            isUser ? "bg-[#f4f6f6]" : "bg-background",
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

          {message.attachments?.length ? (
            <div className="mt-3 flex flex-wrap gap-2 border-t pt-3">
              {message.attachments.map((attachment) => (
                <span
                  key={attachment.id}
                  className="inline-flex items-center gap-1.5 rounded-md bg-background px-2 py-1 text-xs text-muted-foreground ring-1 ring-border"
                >
                  <FileText className="size-3.5" aria-hidden="true" />
                  {attachment.name}
                </span>
              ))}
            </div>
          ) : null}

          {!isUser && message.content ? (
            <div className="mt-3 flex items-center gap-1 border-t pt-2">
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
                  className="ml-1"
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
      <DropdownMenuTrigger asChild>
        <Button variant="outline" className="h-9 bg-background" aria-label="Export or share conversation">
          <Share2 aria-hidden="true" />
          <span className="hidden sm:inline">Export / Share</span>
        </Button>
      </DropdownMenuTrigger>
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
  onOpenStatus,
  onRemoveAttachment,
  onSend,
  onStartVoice,
}: ChatWorkspaceProps) {
  const [itinerarySelection, setItinerarySelection] = useState<{
    message: ChatMessage
    result?: StructuredResult
  } | null>(null)
  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({
      behavior: isStreaming ? "smooth" : "auto",
      block: "end",
    })
  }, [conversation.messages, isStreaming])

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSend()
  }

  return (
    <section className="grid min-h-0 min-w-0 grid-rows-[52px_minmax(0,1fr)_auto] bg-background">
      <header className="flex min-w-0 items-center gap-3 border-b px-3 md:px-4">
        <div className="min-w-0">
          <p className="text-[11px] font-medium uppercase text-muted-foreground">Conversation</p>
          <h1 className="truncate text-sm font-semibold">{conversation.title}</h1>
        </div>
        <span className="ml-auto hidden truncate text-xs text-muted-foreground lg:block">
          {runtime.activity}
        </span>
        <Button
          variant="outline"
          size="icon"
          className="ml-auto xl:hidden"
          onClick={onOpenStatus}
          aria-label="Open trip status"
        >
          <PanelRight aria-hidden="true" />
        </Button>
        <ConversationExport conversation={conversation} />
      </header>

      <div className="min-h-0 overflow-y-auto px-3 py-5 md:px-6" aria-live="polite">
        <div className="mx-auto flex w-full max-w-[900px] flex-col gap-5">
          {conversation.messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              showToolActivity={showToolActivity}
              onOpenItinerary={(selectedMessage, result) =>
                setItinerarySelection({ message: selectedMessage, result })
              }
            />
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="border-t bg-[#fbfcfc] px-3 pb-2 pt-3 md:px-5">
        <form className="mx-auto w-full max-w-[900px]" onSubmit={submit}>
          {attachments.length > 0 ? (
            <div className="mb-2 flex flex-wrap gap-2">
              {attachments.map((attachment) => (
                <span
                  key={attachment.id}
                  className="inline-flex h-7 items-center gap-1.5 rounded-md border bg-background pl-2 pr-1 text-xs"
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

          <div className="rounded-lg border bg-background p-2 shadow-sm focus-within:border-ring focus-within:ring-2 focus-within:ring-ring/20">
            <Textarea
              aria-label="Message TripWeaver"
              placeholder="Type your message..."
              className="max-h-36 min-h-12 resize-none border-0 bg-transparent px-2 py-2 shadow-none focus-visible:ring-0 dark:bg-transparent"
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
                  <Button type="button" variant="ghost" size="icon" aria-label="Attach file" asChild>
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
                    className={cn(isListening && "bg-rose-50 text-rose-700")}
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
                type="submit"
                size="icon-lg"
                className="ml-auto rounded-full bg-[#153e3a] hover:bg-[#205c55]"
                disabled={(!input.trim() && attachments.length === 0) || isStreaming}
                aria-label="Send message"
              >
                {isStreaming ? (
                  <LoaderCircle className="animate-spin" aria-hidden="true" />
                ) : (
                  <ArrowUp aria-hidden="true" />
                )}
              </Button>
            </div>
          </div>
        </form>
        <p className="mt-1.5 text-center text-[10px] text-muted-foreground">
          Travel availability and prices can change. Verify important details before booking.
        </p>
      </div>

      <Dialog
        open={Boolean(itinerarySelection)}
        onOpenChange={(open) => !open && setItinerarySelection(null)}
      >
        <DialogContent className="max-h-[85vh] max-w-2xl overflow-y-auto rounded-lg">
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
