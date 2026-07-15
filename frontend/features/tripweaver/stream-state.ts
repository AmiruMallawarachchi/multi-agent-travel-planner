import type { StreamEvent } from "@/lib/sse"

import type {
  Conversation,
  McpServerName,
  McpServerStatuses,
  RuntimeState,
  ServiceKey,
  ServiceState,
  TripContext,
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

const SERVICE_SERVERS: Record<ServiceKey, McpServerName> = {
  flight: "flight-mcp",
  hotel: "hotel-mcp",
  itinerary: "itinerary-mcp",
  weather: "weather-mcp",
  currency: "currency-mcp",
  location: "location-mcp",
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

export function createRuntimeState(
  backendOnline = false,
  mcpServers: McpServerStatuses = {},
): RuntimeState {
  function initialStatus(key: ServiceKey): ToolStatus {
    if (!backendOnline) return "offline"
    return mcpServers[SERVICE_SERVERS[key]] === "available" ? "idle" : "unavailable"
  }

  return {
    activity: backendOnline ? "Ready" : "Backend offline",
    activeAgent: "TripWeaver router",
    backendOnline,
    mcpServers,
    services: {
      flight: serviceState("flight", initialStatus("flight")),
      hotel: serviceState("hotel", initialStatus("hotel")),
      itinerary: serviceState("itinerary", initialStatus("itinerary")),
      weather: serviceState("weather", initialStatus("weather")),
      currency: serviceState("currency", initialStatus("currency")),
      location: serviceState("location", initialStatus("location")),
    },
  }
}

export function setBackendAvailability(
  runtime: RuntimeState,
  online: boolean,
  mcpServers: McpServerStatuses = runtime.mcpServers,
): RuntimeState {
  const next = createRuntimeState(online, mcpServers)
  return {
    ...next,
    services: Object.fromEntries(
      (Object.keys(next.services) as ServiceKey[]).map((key) => [
        key,
        {
          ...next.services[key],
          status:
            runtime.services[key].status === "running" && next.services[key].status === "idle"
              ? "running"
              : next.services[key].status,
        },
      ]),
    ) as RuntimeState["services"],
  }
}

export function resetRuntimeState(runtime: RuntimeState) {
  return createRuntimeState(runtime.backendOnline, runtime.mcpServers)
}

const TOOL_DETAILS: Record<string, { key: ServiceKey; label: string }> = {
  list_flights: { key: "flight", label: "Flight overview" },
  search_flights: { key: "flight", label: "Flight search" },
  book_flight: { key: "flight", label: "Flight booking" },
  list_hotels: { key: "hotel", label: "Hotel overview" },
  search_hotels: { key: "hotel", label: "Hotel search" },
  book_hotel: { key: "hotel", label: "Hotel booking" },
  create_itinerary: { key: "itinerary", label: "Itinerary planning" },
  get_current_weather: { key: "weather", label: "Current weather" },
  get_weather_forecast: { key: "weather", label: "Weather forecast" },
  convert_currency: { key: "currency", label: "Currency conversion" },
  get_exchange_rate: { key: "currency", label: "Exchange rate" },
  list_supported_currencies: { key: "currency", label: "Supported currencies" },
  resolve_location: { key: "location", label: "Location lookup" },
  search_places: { key: "location", label: "Place search" },
}

function describeTool(tool: string): { key: ServiceKey; activity: ToolActivity } {
  const detail = TOOL_DETAILS[tool] ?? { key: "location" as const, label: "Travel tool" }
  return {
    key: detail.key,
    activity: {
      id: tool,
      label: detail.label,
      server: SERVICE_LABELS[detail.key],
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
  if (normalized.includes("itinerary")) return "Itinerary agent"
  if (normalized.includes("weather")) return "Weather agent"
  if (normalized.includes("currency")) return "Currency agent"
  if (normalized.includes("location")) return "Location agent"
  if (normalized.includes("general")) return "General travel agent"
  return "TripWeaver router"
}

function dataRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

function itineraryContext(current: TripContext, data: unknown): TripContext {
  const itinerary = dataRecord(data)
  if (!itinerary) return current

  const destination =
    typeof itinerary.destination === "string" && itinerary.destination.trim()
      ? itinerary.destination
      : current.destination
  const dates =
    typeof itinerary.start_date === "string" && typeof itinerary.end_date === "string"
      ? `${itinerary.start_date} - ${itinerary.end_date}`
      : current.dates
  const travelers =
    typeof itinerary.travelers === "number" && Number.isFinite(itinerary.travelers)
      ? `${itinerary.travelers.toLocaleString()} travellers`
      : current.travelers
  const budgetData = dataRecord(itinerary.budget)
  const budget =
    typeof budgetData?.total === "number" && Number.isFinite(budgetData.total)
      ? `${typeof budgetData.currency === "string" ? `${budgetData.currency} ` : ""}${budgetData.total.toLocaleString()}`
      : current.budget
  const interests = Array.isArray(itinerary.interests)
    ? itinerary.interests.filter(
        (interest): interest is string => typeof interest === "string" && Boolean(interest.trim()),
      )
    : []

  return {
    destination,
    dates,
    travelers,
    budget,
    preferences: interests.length ? interests : current.preferences,
  }
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
      activeAgent: `${key.charAt(0).toUpperCase()}${key.slice(1)} agent`,
      services: {
        ...runtime.services,
        [key]: { ...runtime.services[key], status },
      },
    }
  } else if (event.type === "result") {
    conversation = {
      ...conversation,
      tripContext:
        event.result_type === "itinerary"
          ? itineraryContext(conversation.tripContext, event.data)
          : conversation.tripContext,
      messages: conversation.messages.map((message) =>
        message.id === assistantMessageId
          ? {
              ...message,
              results: [
                ...(message.results ?? []),
                { type: event.result_type, tool: event.tool, data: event.data },
              ],
            }
          : message,
      ),
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
