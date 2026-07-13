"use client"

import { FormEvent, useMemo, useRef, useState } from "react"
import { ArrowUp, Copy, Menu, Mic, Plus, Search, SquarePen } from "lucide-react"

import { Markdown } from "@/components/prompt-kit/markdown"
import { parseSseChunk, type StreamEvent } from "@/lib/sse"
import { cn } from "@/lib/utils"

type Message = {
  id: string
  role: "assistant" | "user"
  content: string
}

const STARTER_MESSAGE = `Hi, I am TripWeaver. Tell me where you want to go and I will help with travel ideas, hotels, flights, or booking steps.

\`\`\`css
.trip {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 1rem;
}
\`\`\``

const QUICK_PROMPTS = [
  "Find hotels in Paris for 2 adults, Sep 10-14",
  "Search flights from Colombo to London on 2026-09-01",
  "What should I plan for 4 days in Kyoto?",
]

const ACTIVITY_LABELS: Record<string, string> = {
  ROUTING: "Routing",
  SEARCHING: "Searching",
  BOOKING: "Booking",
  RESPONDING: "Responding",
  CLARIFYING: "Clarifying",
}

function newId() {
  return crypto.randomUUID()
}

export function SimpleChat() {
  const [messages, setMessages] = useState<Message[]>([
    { id: newId(), role: "assistant", content: STARTER_MESSAGE },
  ])
  const [input, setInput] = useState("")
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [activity, setActivity] = useState("Ready")
  const [isStreaming, setIsStreaming] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const activeTitle = useMemo(() => {
    const firstUserMessage = messages.find((message) => message.role === "user")
    return firstUserMessage?.content.slice(0, 42) || "Project roadmap discussion"
  }, [messages])

  function startNewChat() {
    abortRef.current?.abort()
    setMessages([{ id: newId(), role: "assistant", content: STARTER_MESSAGE }])
    setSessionId(null)
    setInput("")
    setActivity("Ready")
    setIsStreaming(false)
  }

  function applyEvent(event: StreamEvent, assistantId: string) {
    if (event.type === "session") {
      setSessionId(event.session_id)
      return
    }

    if (event.type === "status") {
      setActivity(ACTIVITY_LABELS[event.state] ?? event.state)
      return
    }

    if (event.type === "tool") {
      setActivity(`${event.status.toLowerCase()} ${event.tool.replaceAll("_", " ")}`)
      return
    }

    if (event.type === "token") {
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId
            ? { ...message, content: `${message.content}${event.content}` }
            : message,
        ),
      )
      return
    }

    if (event.type === "error") {
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId ? { ...message, content: event.message } : message,
        ),
      )
      setActivity("Error")
      return
    }

    if (event.type === "done") {
      setActivity("Ready")
    }
  }

  async function sendMessage(value = input) {
    const message = value.trim()
    if (!message || isStreaming) {
      return
    }

    const userMessage: Message = { id: newId(), role: "user", content: message }
    const assistantMessage: Message = { id: newId(), role: "assistant", content: "" }

    setMessages((current) => [...current, userMessage, assistantMessage])
    setInput("")
    setIsStreaming(true)
    setActivity("Connecting")

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, session_id: sessionId }),
        signal: controller.signal,
      })

      if (!response.ok || !response.body) {
        throw new Error(`Request failed with ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          break
        }

        buffer += decoder.decode(value, { stream: true })
        const parsed = parseSseChunk(buffer)
        buffer = parsed.remainder
        parsed.events.forEach((event) => applyEvent(event, assistantMessage.id))
      }
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        setMessages((current) =>
          current.map((messageItem) =>
            messageItem.id === assistantMessage.id
              ? {
                  ...messageItem,
                  content:
                    "I could not reach the TripWeaver backend right now. Check the backend service and try again.",
                }
              : messageItem,
          ),
        )
        setActivity("Offline")
      }
    } finally {
      setIsStreaming(false)
      abortRef.current = null
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void sendMessage()
  }

  return (
    <main className="chat-shell">
      <aside className="chat-sidebar">
        <div className="brand-row">
          <div className="brand-mark" aria-hidden />
          <span>tripweaver.chat</span>
          <Search className="sidebar-icon" aria-hidden />
        </div>

        <button className="new-chat-button" onClick={startNewChat} type="button">
          <Plus size={18} aria-hidden />
          New Chat
        </button>

        <nav className="history-list" aria-label="Chat history">
          <p>Today</p>
          <button className="history-item active" type="button">
            {activeTitle}
          </button>
          <button className="history-item" type="button">
            API Documentation Review
          </button>
          <button className="history-item" type="button">
            Frontend Bug Analysis
          </button>
          <p>Yesterday</p>
          <button className="history-item" type="button">
            Database Schema Design
          </button>
          <button className="history-item" type="button">
            Performance Optimization
          </button>
          <p>Last 7 days</p>
          <button className="history-item" type="button">
            Component Library
          </button>
        </nav>
      </aside>

      <section className="chat-panel">
        <header className="chat-header">
          <button className="icon-button mobile-only" type="button" aria-label="Open navigation">
            <Menu size={19} aria-hidden />
          </button>
          <SquarePen size={19} aria-hidden />
          <h1>{activeTitle}</h1>
          <span className={cn("activity-pill", isStreaming && "active")}>{activity}</span>
        </header>

        <div className="message-scroll">
          <div className="message-stack">
            {messages.map((message) => (
              <article className={cn("message-row", message.role)} key={message.id}>
                <div className="message-content">
                  {message.content ? (
                    <Markdown>{message.content}</Markdown>
                  ) : (
                    <span className="typing-line">Thinking...</span>
                  )}
                  {message.role === "assistant" && message.content ? (
                    <div className="message-actions">
                      <button type="button" aria-label="Copy response">
                        <Copy size={16} aria-hidden />
                      </button>
                    </div>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        </div>

        <div className="prompt-dock">
          <div className="quick-prompts">
            {QUICK_PROMPTS.map((prompt) => (
              <button
                disabled={isStreaming}
                key={prompt}
                onClick={() => void sendMessage(prompt)}
                type="button"
              >
                {prompt}
              </button>
            ))}
          </div>

          <form className="composer" onSubmit={submit}>
            <textarea
              aria-label="Message TripWeaver"
              disabled={isStreaming}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault()
                  void sendMessage()
                }
              }}
              placeholder="Ask anything"
              rows={1}
              value={input}
            />
            <div className="composer-actions">
              <button className="icon-button" type="button" aria-label="Attach">
                <Plus size={19} aria-hidden />
              </button>
              <button className="search-chip" type="button">
                <Search size={17} aria-hidden />
                Search
              </button>
              <button className="icon-button" type="button" aria-label="Voice input">
                <Mic size={18} aria-hidden />
              </button>
              <button
                className="send-button"
                disabled={!input.trim() || isStreaming}
                type="submit"
                aria-label="Send message"
              >
                <ArrowUp size={19} aria-hidden />
              </button>
            </div>
          </form>
        </div>
      </section>
    </main>
  )
}
