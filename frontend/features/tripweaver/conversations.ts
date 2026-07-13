import type { Conversation, TripContext } from "./types"

export const CONVERSATIONS_STORAGE_KEY = "tripweaver.conversations.v1"
export const SETTINGS_STORAGE_KEY = "tripweaver.settings.v1"

export const EMPTY_TRIP_CONTEXT: TripContext = {
  destination: null,
  dates: null,
  travelers: null,
  budget: null,
  preferences: [],
}

const WELCOME_MESSAGE =
  "Hi, I am TripWeaver. Tell me where you want to go, and I will help with travel ideas, hotels, flights, and booking steps."

function createId() {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function createConversation(now = new Date(), id = createId()): Conversation {
  const timestamp = now.toISOString()

  return {
    id,
    title: "New trip",
    sessionId: null,
    createdAt: timestamp,
    updatedAt: timestamp,
    tripContext: { ...EMPTY_TRIP_CONTEXT, preferences: [] },
    messages: [
      {
        id: `${id}-welcome`,
        role: "assistant",
        content: WELCOME_MESSAGE,
        createdAt: timestamp,
      },
    ],
  }
}

export function hasUserMessage(conversation: Conversation) {
  return conversation.messages.some((message) => message.role === "user")
}

export function deriveConversationTitle(message: string) {
  const normalized = message.replace(/\s+/g, " ").trim()
  if (normalized.length <= 48) {
    return normalized || "New trip"
  }
  return `${normalized.slice(0, 45).trimEnd()}...`
}

export function searchConversations(conversations: Conversation[], query: string) {
  const normalized = query.trim().toLocaleLowerCase()
  if (!normalized) {
    return conversations
  }

  return conversations.filter(
    (conversation) =>
      conversation.title.toLocaleLowerCase().includes(normalized) ||
      conversation.messages.some((message) => message.content.toLocaleLowerCase().includes(normalized)),
  )
}

function startOfDay(value: Date) {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate()).getTime()
}

export function groupConversations(conversations: Conversation[], now = new Date()) {
  const today = startOfDay(now)
  const day = 24 * 60 * 60 * 1000
  const buckets = new Map<string, Conversation[]>([
    ["Today", []],
    ["Yesterday", []],
    ["Previous 7 days", []],
    ["Earlier", []],
  ])

  conversations
    .toSorted((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt))
    .forEach((conversation) => {
      const difference = today - startOfDay(new Date(conversation.updatedAt))
      const label =
        difference <= 0
          ? "Today"
          : difference === day
            ? "Yesterday"
            : difference < 7 * day
              ? "Previous 7 days"
              : "Earlier"
      buckets.get(label)?.push(conversation)
    })

  return Array.from(buckets, ([label, grouped]) => ({ label, conversations: grouped })).filter(
    ({ conversations: grouped }) => grouped.length > 0,
  )
}

function isConversation(value: unknown): value is Conversation {
  if (!value || typeof value !== "object") {
    return false
  }

  const candidate = value as Partial<Conversation>
  return (
    typeof candidate.id === "string" &&
    typeof candidate.title === "string" &&
    typeof candidate.createdAt === "string" &&
    typeof candidate.updatedAt === "string" &&
    Array.isArray(candidate.messages) &&
    candidate.messages.every(
      (message) =>
        message &&
        typeof message.id === "string" &&
        (message.role === "assistant" || message.role === "user") &&
        typeof message.content === "string" &&
        typeof message.createdAt === "string",
    ) &&
    Boolean(candidate.tripContext)
  )
}

export function parseStoredConversations(raw: string | null) {
  if (!raw) {
    return []
  }

  try {
    const parsed: unknown = JSON.parse(raw)
    return Array.isArray(parsed) && parsed.every(isConversation) ? parsed : []
  } catch {
    return []
  }
}

export function exportConversation(conversation: Conversation) {
  const lines = conversation.messages.flatMap((message) => {
    const speaker = message.role === "user" ? "You" : "TripWeaver AI"
    const attachments = message.attachments?.length
      ? `\nAttachments: ${message.attachments.map(({ name }) => name).join(", ")}`
      : ""
    return [`${speaker}: ${message.content}${attachments}`, ""]
  })

  return [`TripWeaver - ${conversation.title}`, `Exported ${new Date().toLocaleString()}`, "", ...lines]
    .join("\n")
    .trim()
}

export function formatConversationTime(timestamp: string) {
  const date = new Date(timestamp)
  return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(date)
}
