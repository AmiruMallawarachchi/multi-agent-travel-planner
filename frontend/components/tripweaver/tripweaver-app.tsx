"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { toast } from "sonner"

import { AppHeader } from "@/components/tripweaver/app-header"
import { AuthDialog, type AuthMode } from "@/components/tripweaver/auth-dialog"
import { ChatWorkspace } from "@/components/tripweaver/chat-workspace"
import { ConversationSidebar } from "@/components/tripweaver/conversation-sidebar"
import { HelpCenterDialog } from "@/components/tripweaver/help-center-dialog"
import { SettingsDialog } from "@/components/tripweaver/settings-dialog"
import { StatusPanel } from "@/components/tripweaver/status-panel"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import {
  CONVERSATIONS_STORAGE_KEY,
  SETTINGS_STORAGE_KEY,
  createConversation,
  deriveConversationTitle,
  hasUserMessage,
  parseStoredConversations,
} from "@/features/tripweaver/conversations"
import {
  applyStreamEvent,
  createRuntimeState,
  resetRuntimeState,
  setBackendAvailability,
} from "@/features/tripweaver/stream-state"
import { extractTripContext } from "@/features/tripweaver/trip-context"
import type {
  Attachment,
  AccountUser,
  ChatMessage,
  Conversation,
  RuntimeState,
  McpServerStatuses,
  TripWeaverSettings,
} from "@/features/tripweaver/types"
import { parseSseChunk, type StreamEvent } from "@/lib/sse"
import { cn } from "@/lib/utils"

const DEFAULT_SETTINGS: TripWeaverSettings = {
  autoSave: true,
  showToolActivity: true,
}

const SIDEBAR_STORAGE_KEY = "tripweaver.sidebars.v1"

interface AppState {
  conversations: Conversation[]
  activeConversationId: string
  runtime: RuntimeState
}

interface SpeechRecognitionResultEvent {
  results: ArrayLike<{ 0: { transcript: string } }>
}

interface SpeechRecognitionInstance {
  continuous: boolean
  interimResults: boolean
  lang: string
  onend: (() => void) | null
  onerror: (() => void) | null
  onresult: ((event: SpeechRecognitionResultEvent) => void) | null
  start: () => void
  stop: () => void
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionInstance

function browserSpeechRecognition() {
  const browser = window as typeof window & {
    SpeechRecognition?: SpeechRecognitionConstructor
    webkitSpeechRecognition?: SpeechRecognitionConstructor
  }
  return browser.SpeechRecognition ?? browser.webkitSpeechRecognition
}

function createInitialState(): AppState {
  const conversation = createConversation()
  return {
    conversations: [conversation],
    activeConversationId: conversation.id,
    runtime: createRuntimeState(false),
  }
}

function parseSettings(raw: string | null): TripWeaverSettings {
  if (!raw) return DEFAULT_SETTINGS
  try {
    const parsed = JSON.parse(raw) as Partial<TripWeaverSettings>
    return {
      autoSave: typeof parsed.autoSave === "boolean" ? parsed.autoSave : true,
      showToolActivity:
        typeof parsed.showToolActivity === "boolean" ? parsed.showToolActivity : true,
    }
  } catch {
    return DEFAULT_SETTINGS
  }
}

function readFile(file: File) {
  if (typeof file.text === "function") {
    return file.text()
  }

  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result ?? ""))
    reader.onerror = () => reject(reader.error)
    reader.readAsText(file)
  })
}

function newId() {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function TripWeaverApp() {
  const [state, setState] = useState<AppState>(createInitialState)
  const [settings, setSettings] = useState<TripWeaverSettings>(DEFAULT_SETTINGS)
  const [query, setQuery] = useState("")
  const [input, setInput] = useState("")
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [statusOpen, setStatusOpen] = useState(false)
  const [desktopHistoryOpen, setDesktopHistoryOpen] = useState(false)
  const [desktopToolsOpen, setDesktopToolsOpen] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [helpOpen, setHelpOpen] = useState(false)
  const [authMode, setAuthMode] = useState<AuthMode | null>(null)
  const [account, setAccount] = useState<AccountUser | null>(null)
  const hydratedRef = useRef(false)
  const abortRef = useRef<AbortController | null>(null)
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null)

  const activeConversation =
    state.conversations.find(({ id }) => id === state.activeConversationId) ?? state.conversations[0]

  const loadAccountConversations = useCallback(async () => {
    const response = await fetch("/api/conversations", { cache: "no-store" })
    if (!response.ok) return
    const data = (await response.json()) as { conversations?: unknown[] }
    const cloud = parseStoredConversations(JSON.stringify(data.conversations ?? []))
    if (cloud.length === 0) return
    setState((current) => ({
      ...current,
      conversations: cloud,
      activeConversationId: cloud[0].id,
      runtime: resetRuntimeState(current.runtime),
    }))
  }, [])

  const refreshAccount = useCallback(async () => {
    try {
      const response = await fetch("/api/auth/me", { cache: "no-store" })
      if (!response.ok) return
      const user = (await response.json()) as AccountUser
      setAccount(user)
      await loadAccountConversations()
    } catch {
      setAccount(null)
    }
  }, [loadAccountConversations])

  useEffect(() => {
    const stored = parseStoredConversations(window.localStorage.getItem(CONVERSATIONS_STORAGE_KEY))
    setSettings(parseSettings(window.localStorage.getItem(SETTINGS_STORAGE_KEY)))
    try {
      const sidebars = JSON.parse(window.localStorage.getItem(SIDEBAR_STORAGE_KEY) ?? "{}") as {
        history?: boolean
        tools?: boolean
      }
      if (typeof sidebars.history === "boolean") setDesktopHistoryOpen(sidebars.history)
      if (typeof sidebars.tools === "boolean") setDesktopToolsOpen(sidebars.tools)
    } catch {
      window.localStorage.removeItem(SIDEBAR_STORAGE_KEY)
    }

    if (stored.length > 0) {
      const sorted = stored.toSorted(
        (left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt),
      )
      setState((current) => ({
        ...current,
        conversations: sorted,
        activeConversationId: sorted[0].id,
      }))
    }
    hydratedRef.current = true
  }, [])

  useEffect(() => {
    if (!hydratedRef.current) return
    window.localStorage.setItem(
      SIDEBAR_STORAGE_KEY,
      JSON.stringify({ history: desktopHistoryOpen, tools: desktopToolsOpen }),
    )
  }, [desktopHistoryOpen, desktopToolsOpen])

  useEffect(() => {
    void refreshAccount()
  }, [refreshAccount])

  useEffect(() => {
    if (!hydratedRef.current) return
    window.localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings))
    if (settings.autoSave) {
      window.localStorage.setItem(CONVERSATIONS_STORAGE_KEY, JSON.stringify(state.conversations))
    } else {
      window.localStorage.removeItem(CONVERSATIONS_STORAGE_KEY)
    }
  }, [settings, state.conversations])

  useEffect(() => {
    if (!hydratedRef.current || !account) return
    const timeout = window.setTimeout(() => {
      state.conversations
        .filter(hasUserMessage)
        .forEach((conversation) => void saveAccountConversation(conversation))
    }, 500)
    return () => window.clearTimeout(timeout)
  }, [account, state.conversations])

  useEffect(() => {
    const controller = new AbortController()

    async function checkBackend() {
      try {
        const response = await fetch("/api/health", { cache: "no-store", signal: controller.signal })
        const health = (await response.json()) as {
          backend?: string
          online?: boolean
          mcp_servers?: McpServerStatuses
        }
        const online = response.ok && health.online === true && health.backend === "online"
        setState((current) => ({
          ...current,
          runtime: setBackendAvailability(current.runtime, online, health.mcp_servers ?? {}),
        }))
      } catch {
        if (!controller.signal.aborted) {
          setState((current) => ({
            ...current,
            runtime: setBackendAvailability(current.runtime, false),
          }))
        }
      }
    }

    void checkBackend()
    const healthInterval = window.setInterval(() => void checkBackend(), 15_000)
    return () => {
      window.clearInterval(healthInterval)
      controller.abort()
    }
  }, [])

  useEffect(
    () => () => {
      abortRef.current?.abort()
      recognitionRef.current?.stop()
    },
    [],
  )

  function startNewChat() {
    abortRef.current?.abort()
    recognitionRef.current?.stop()
    const conversation = createConversation()
    setState((current) => ({
      conversations: [conversation, ...current.conversations.filter(hasUserMessage)],
      activeConversationId: conversation.id,
      runtime: resetRuntimeState(current.runtime),
    }))
    setInput("")
    setAttachments([])
    setIsStreaming(false)
    setHistoryOpen(false)
  }

  function clearConversations() {
    abortRef.current?.abort()
    const conversation = createConversation()
    window.localStorage.removeItem(CONVERSATIONS_STORAGE_KEY)
    if (account) {
      void fetch("/api/conversations", { method: "DELETE" })
    }
    setState((current) => ({
      conversations: [conversation],
      activeConversationId: conversation.id,
      runtime: resetRuntimeState(current.runtime),
    }))
    setInput("")
    setAttachments([])
    setQuery("")
    setIsStreaming(false)
  }

  async function saveAccountConversation(conversation: Conversation) {
    try {
      await fetch("/api/conversations", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation }),
      })
    } catch {
      // A failed background sync should not interrupt trip planning.
    }
  }

  async function authenticate(
    mode: AuthMode,
    payload: { email: string; password: string; name?: string },
  ) {
    const response = await fetch(`/api/auth/${mode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
    const body = (await response.json()) as { user?: AccountUser; detail?: string }
    if (!response.ok || !body.user) {
      throw new Error(body.detail ?? "Could not authenticate")
    }
    setAccount(body.user)
    setAuthMode(null)
    toast.success(mode === "register" ? "Account created" : "Signed in")
    await loadAccountConversations()
  }

  async function signOut() {
    abortRef.current?.abort()
    recognitionRef.current?.stop()
    await fetch("/api/auth/logout", { method: "POST" })
    setAccount(null)
    setState(createInitialState())
    setInput("")
    setAttachments([])
    setIsStreaming(false)
    toast.success("Signed out")
  }

  function selectConversation(conversationId: string) {
    setState((current) => ({
      ...current,
      activeConversationId: conversationId,
      runtime: resetRuntimeState(current.runtime),
    }))
    setInput("")
    setAttachments([])
    setHistoryOpen(false)
  }

  async function attachFiles(fileList: FileList | null) {
    if (!fileList) return

    const accepted: Attachment[] = []
    for (const file of Array.from(fileList).slice(0, 3)) {
      if (file.size > 1024 * 1024) {
        toast.error(`${file.name} is larger than 1 MB`)
        continue
      }
      try {
        accepted.push({
          id: newId(),
          name: file.name,
          type: file.type || "text/plain",
          size: file.size,
          content: await readFile(file),
        })
      } catch {
        toast.error(`Could not read ${file.name}`)
      }
    }

    setAttachments((current) => [...current, ...accepted].slice(0, 3))
  }

  function applyEvent(conversationId: string, assistantMessageId: string, event: StreamEvent) {
    setState((current) => {
      const conversation = current.conversations.find(({ id }) => id === conversationId)
      if (!conversation) return current

      const next = applyStreamEvent(
        { conversation, runtime: current.runtime },
        assistantMessageId,
        event,
      )
      return {
        ...current,
        conversations: current.conversations.map((item) =>
          item.id === conversationId ? next.conversation : item,
        ),
        runtime: next.runtime,
      }
    })
  }

  async function sendMessage(value = input) {
    const content = value.trim() || (attachments.length ? "Please use the attached files for this trip." : "")
    if (!content || isStreaming || !activeConversation) return

    const now = new Date().toISOString()
    const conversationId = activeConversation.id
    const assistantMessageId = newId()
    const hadUserMessage = hasUserMessage(activeConversation)
    const attachmentMetadata = attachments.map(({ id, name, type, size }) => ({ id, name, type, size }))
    const userMessage: ChatMessage = {
      id: newId(),
      role: "user",
      content,
      createdAt: now,
      attachments: attachmentMetadata,
    }
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      createdAt: now,
      tools: [],
      results: [],
    }
    const requestMessage = [
      content,
      ...attachments.map(
        (attachment) =>
          `<attachment name="${attachment.name}">\n${attachment.content.slice(0, 15_000)}\n</attachment>`,
      ),
    ].join("\n\n")

    setState((current) => ({
      ...current,
      conversations: current.conversations.map((conversation) =>
        conversation.id === conversationId
          ? {
              ...conversation,
              title: hadUserMessage ? conversation.title : deriveConversationTitle(content),
              updatedAt: now,
              tripContext: extractTripContext(content, conversation.tripContext),
              messages: [...conversation.messages, userMessage, assistantMessage],
            }
          : conversation,
      ),
      runtime: resetRuntimeState(current.runtime),
    }))
    setInput("")
    setAttachments([])
    setIsStreaming(true)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: requestMessage,
          session_id: activeConversation.sessionId,
        }),
        signal: controller.signal,
      })

      if (!response.ok || !response.body) {
        throw new Error(`Chat request failed with ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value: chunk } = await reader.read()
        if (done) break

        buffer += decoder.decode(chunk, { stream: true })
        const parsed = parseSseChunk(buffer)
        buffer = parsed.remainder
        parsed.events.forEach((event) => applyEvent(conversationId, assistantMessageId, event))
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        applyEvent(conversationId, assistantMessageId, {
          type: "error",
          message: "Response stopped.",
        })
        applyEvent(conversationId, assistantMessageId, { type: "done" })
      } else {
        applyEvent(conversationId, assistantMessageId, {
          type: "error",
          message:
            "I could not complete that request. Check that the TripWeaver backend and API credentials are available, then try again.",
        })
        toast.error("TripWeaver could not complete the request")
      }
    } finally {
      setIsStreaming(false)
      abortRef.current = null
    }
  }

  function startVoiceInput() {
    const Recognition = browserSpeechRecognition()
    if (!Recognition) {
      toast.info("Voice input is not supported by this browser")
      return
    }

    recognitionRef.current?.stop()
    const recognition = new Recognition()
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = "en-US"
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript?.trim()
      if (transcript) setInput((current) => `${current}${current ? " " : ""}${transcript}`)
    }
    recognition.onerror = () => {
      setIsListening(false)
      toast.error("Voice input could not start")
    }
    recognition.onend = () => setIsListening(false)
    recognitionRef.current = recognition
    setIsListening(true)
    recognition.start()
  }

  if (!activeConversation) return null

  function isCompactViewport() {
    return window.matchMedia("(max-width: 1023px)").matches
  }

  async function deleteConversation(conversationId: string) {
    if (account) {
      try {
        const response = await fetch(`/api/conversations?id=${encodeURIComponent(conversationId)}`, {
          method: "DELETE",
        })
        if (!response.ok) throw new Error("Delete failed")
      } catch {
        toast.error("Could not delete this conversation")
        return
      }
    }

    if (conversationId === state.activeConversationId) {
      abortRef.current?.abort()
    }
    setState((current) => {
      const remaining = current.conversations.filter(({ id }) => id !== conversationId)
      const fallback = remaining[0] ?? createConversation()
      return {
        conversations: remaining.length > 0 ? remaining : [fallback],
        activeConversationId:
          current.activeConversationId === conversationId
            ? fallback.id
            : current.activeConversationId,
        runtime:
          current.activeConversationId === conversationId
            ? resetRuntimeState(current.runtime)
            : current.runtime,
      }
    })
    toast.success("Conversation deleted")
  }

  function pinConversation(conversationId: string, pinned: boolean) {
    setState((current) => ({
      ...current,
      conversations: current.conversations.map((conversation) =>
        conversation.id === conversationId ? { ...conversation, pinned } : conversation,
      ),
    }))
  }

  function renameConversation(conversationId: string, title: string) {
    const updatedAt = new Date().toISOString()
    setState((current) => ({
      ...current,
      conversations: current.conversations.map((conversation) =>
        conversation.id === conversationId ? { ...conversation, title, updatedAt } : conversation,
      ),
    }))
  }

  function answerQuickReply(messageId: string, value: string) {
    setState((current) => ({
      ...current,
      conversations: current.conversations.map((conversation) =>
        conversation.id === current.activeConversationId
          ? {
              ...conversation,
              messages: conversation.messages.map((message) =>
                message.id === messageId && message.quickReplies
                  ? {
                      ...message,
                      quickReplies: { ...message.quickReplies, answeredValue: value },
                    }
                  : message,
              ),
            }
          : conversation,
      ),
    }))
    void sendMessage(value)
  }

  function toggleHistory() {
    if (isCompactViewport()) {
      setHistoryOpen((open) => !open)
      return
    }
    setDesktopHistoryOpen((open) => !open)
  }

  function toggleTools() {
    if (isCompactViewport()) {
      setStatusOpen((open) => !open)
      return
    }
    setDesktopToolsOpen((open) => !open)
  }

  const sidebar = (
    <ConversationSidebar
      activeConversationId={activeConversation.id}
      conversations={state.conversations}
      query={query}
      onDelete={(conversationId) => void deleteConversation(conversationId)}
      onNewChat={startNewChat}
      onPin={pinConversation}
      onQueryChange={setQuery}
      onRename={renameConversation}
      onSelect={selectConversation}
    />
  )

  const statusPanel = (
    <StatusPanel
      runtime={state.runtime}
      tripContext={activeConversation.tripContext}
      onQuickAction={(prompt) => {
        setInput(prompt)
        setStatusOpen(false)
      }}
    />
  )

  return (
    <main className="tw-app-background h-dvh min-h-[520px] overflow-hidden">
      <div className="grid h-full w-full grid-rows-[56px_minmax(0,1fr)] gap-1.5 overflow-hidden p-1.5 sm:grid-rows-[58px_minmax(0,1fr)] sm:gap-2 sm:p-2">
        <AppHeader
          account={account}
          backendOnline={state.runtime.backendOnline}
          historyOpen={desktopHistoryOpen || historyOpen}
          toolsOpen={desktopToolsOpen || statusOpen}
          onOpenAuth={setAuthMode}
          onOpenHelp={() => setHelpOpen(true)}
          onOpenSettings={() => setSettingsOpen(true)}
          onSignOut={() => void signOut()}
          onToggleHistory={toggleHistory}
          onToggleTools={toggleTools}
        />

        <div
          className={cn(
            "grid min-h-0 min-w-0 grid-cols-1 gap-1.5 transition-[grid-template-columns] duration-200 sm:gap-2",
            desktopToolsOpen && desktopHistoryOpen &&
              "lg:grid-cols-[280px_minmax(0,1fr)_280px]",
            desktopToolsOpen && !desktopHistoryOpen &&
              "lg:grid-cols-[280px_minmax(0,1fr)]",
            !desktopToolsOpen && desktopHistoryOpen &&
              "lg:grid-cols-[minmax(0,1fr)_280px]",
            !desktopToolsOpen && !desktopHistoryOpen && "lg:grid-cols-[minmax(0,1fr)]",
          )}
        >
          {desktopToolsOpen ? (
            <div className="glass-panel hidden min-h-0 overflow-y-auto rounded-xl lg:block">
              {statusPanel}
            </div>
          ) : null}
          <ChatWorkspace
            attachments={attachments}
            conversation={activeConversation}
            input={input}
            isListening={isListening}
            isStreaming={isStreaming}
            runtime={state.runtime}
            showToolActivity={settings.showToolActivity}
            onAttachments={(files) => void attachFiles(files)}
            onInputChange={setInput}
            onQuickReply={answerQuickReply}
            onRemoveAttachment={(attachmentId) =>
              setAttachments((current) => current.filter(({ id }) => id !== attachmentId))
            }
            onSend={(message) => void sendMessage(message)}
            onStartVoice={startVoiceInput}
            onStop={() => abortRef.current?.abort()}
          />
          {desktopHistoryOpen ? (
            <div className="glass-panel hidden min-h-0 overflow-hidden rounded-xl lg:block">
              {sidebar}
            </div>
          ) : null}
        </div>
      </div>

      <Sheet open={historyOpen} onOpenChange={setHistoryOpen}>
        <SheetContent side="left" className="w-[min(92vw,340px)] gap-0 overflow-hidden p-0">
          <SheetHeader className="sr-only">
            <SheetTitle>Conversation history</SheetTitle>
            <SheetDescription>Search and open saved TripWeaver conversations.</SheetDescription>
          </SheetHeader>
          {sidebar}
        </SheetContent>
      </Sheet>

      <Sheet open={statusOpen} onOpenChange={setStatusOpen}>
        <SheetContent side="right" className="w-[min(94vw,360px)] gap-0 overflow-y-auto p-0">
          <SheetHeader className="sr-only">
            <SheetTitle>Trip status</SheetTitle>
            <SheetDescription>Live tools, trip context, and quick actions.</SheetDescription>
          </SheetHeader>
          {statusPanel}
        </SheetContent>
      </Sheet>

      <SettingsDialog
        historyCount={state.conversations.filter(hasUserMessage).length}
        open={settingsOpen}
        settings={settings}
        onClearHistory={clearConversations}
        onOpenChange={setSettingsOpen}
        onSettingsChange={setSettings}
      />
      <AuthDialog mode={authMode} onModeChange={setAuthMode} onSubmit={authenticate} />
      <HelpCenterDialog open={helpOpen} onOpenChange={setHelpOpen} />
    </main>
  )
}
