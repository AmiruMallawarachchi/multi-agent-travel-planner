import type { StreamEvent } from "@/lib/sse"

import type {
  Conversation,
  RuntimeState,
  ServiceKey,
  ServiceState,
  ToolActivity,
  ToolStatus,
} from "./types"

const SERVICE_LABELS: Record<ServiceKey, string> = {
  flight: "Flight MCP",
  hotel: "Hotel MCP",
  itinerary: "Itinerary MCP",
  weather: "Weather MCP",
  currency: "Currency MCP",
  location: "Location MCP",
}

const ACTIVITY_LABELS: Record<string, string> = {
  ROUTING: "Routing request",
  SEARCHING: "Searching travel options",
  BOOKING: "Preparing booking",
  RESPONDING: "Writing response",
  CLARIFYING: "Checking trip details",
}

function serviceState(key: ServiceKey, status: ToolStatus): ServiceState {
  return { key, label: SERVICE_LABELS[key], status }
}

export function createRuntimeState(backendOnline = false): RuntimeState {
  const supportedStatus: ToolStatus = backendOnline ? "idle" : "offline"
  return {
    activity: backendOnline ? "Ready" : "Backend offline",
    activeAgent: "TripWeaver router",
    backendOnline,
    services: {
      flight: serviceState("flight", supportedStatus),
      hotel: serviceState("hotel", supportedStatus),
      itinerary: serviceState("itinerary", "unavailable"),
      weather: serviceState("weather", "unavailable"),
      currency: serviceState("currency", "unavailable"),
      location: serviceState("location", "unavailable"),
    },
  }
}

export function setBackendAvailability(runtime: RuntimeState, online: boolean): RuntimeState {
  const next = createRuntimeState(online)
  return {
    ...next,
    services: {
      ...next.services,
      flight: {
        ...next.services.flight,
        status: runtime.services.flight.status === "running" ? "running" : next.services.flight.status,
      },
      hotel: {
        ...next.services.hotel,
        status: runtime.services.hotel.status === "running" ? "running" : next.services.hotel.status,
      },
    },
  }
}

function describeTool(tool: string): { key: "flight" | "hotel"; activity: ToolActivity } {
  const normalized = tool.toLocaleLowerCase()
  const key = normalized.includes("hotel") ? "hotel" : "flight"
  const action = normalized.includes("book") ? "booking" : "search"
  const subject = key === "hotel" ? "Hotel" : "Flight"
  return {
    key,
    activity: {
      id: tool,
      label: `${subject} ${action}`,
      server: SERVICE_LABELS[key],
      status: "running",
    },
  }
}

function eventToolStatus(status: string): ToolStatus {
  if (status === "SUCCEEDED") {
    return "completed"
  }
  if (status === "FAILED") {
    return "failed"
  }
  return "running"
}

function activeAgent(node?: string) {
  const normalized = node?.toLocaleLowerCase() ?? ""
  if (normalized.includes("hotel")) return "Hotel agent"
  if (normalized.includes("flight")) return "Flight agent"
  if (normalized.includes("general")) return "General travel agent"
  return "TripWeaver router"
}

export interface StreamState {
  conversation: Conversation
  runtime: RuntimeState
}

export function applyStreamEvent(
  state: StreamState,
  assistantMessageId: string,
  event: StreamEvent,
): StreamState {
  let conversation = state.conversation
  let runtime = state.runtime

  if (event.type === "session") {
    conversation = { ...conversation, sessionId: event.session_id }
  } else if (event.type === "status") {
    runtime = {
      ...runtime,
      activity: ACTIVITY_LABELS[event.state] ?? event.state,
      activeAgent: activeAgent(event.node),
    }
  } else if (event.type === "tool") {
    const { key, activity } = describeTool(event.tool)
    const status = eventToolStatus(event.status)
    const messages = conversation.messages.map((message) => {
      if (message.id !== assistantMessageId) {
        return message
      }
      const tools = message.tools ?? []
      const nextTool = { ...activity, status }
      return {
        ...message,
        tools: tools.some(({ id }) => id === event.tool)
          ? tools.map((tool) => (tool.id === event.tool ? nextTool : tool))
          : [...tools, nextTool],
      }
    })
    conversation = { ...conversation, messages }
    runtime = {
      ...runtime,
      activity: status === "running" ? `${activity.label} in progress` : `${activity.label} ${status}`,
      activeAgent: key === "hotel" ? "Hotel agent" : "Flight agent",
      services: {
        ...runtime.services,
        [key]: { ...runtime.services[key], status },
      },
    }
  } else if (event.type === "token") {
    conversation = {
      ...conversation,
      messages: conversation.messages.map((message) =>
        message.id === assistantMessageId
          ? { ...message, content: `${message.content}${event.content}` }
          : message,
      ),
    }
    runtime = { ...runtime, activity: "Writing response" }
  } else if (event.type === "error") {
    conversation = {
      ...conversation,
      messages: conversation.messages.map((message) =>
        message.id === assistantMessageId
          ? { ...message, content: message.content || event.message }
          : message,
      ),
    }
    runtime = { ...runtime, activity: "Request failed" }
  } else if (event.type === "done") {
    runtime = { ...runtime, activity: "Ready", activeAgent: "TripWeaver router" }
  }

  return { conversation, runtime }
}
