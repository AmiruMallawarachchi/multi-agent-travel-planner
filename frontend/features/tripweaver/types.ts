export type MessageRole = "assistant" | "user"

export type ToolStatus = "idle" | "running" | "completed" | "failed" | "offline" | "unavailable"

export type ServiceKey = "flight" | "hotel" | "itinerary" | "weather" | "currency" | "location"

export type McpServerName =
  | "flight-mcp"
  | "hotel-mcp"
  | "itinerary-mcp"
  | "weather-mcp"
  | "currency-mcp"
  | "location-mcp"

export type McpServerStatus = "available" | "unavailable"

export type McpServerStatuses = Partial<Record<McpServerName, McpServerStatus>>

export type StructuredResultType =
  | "flight"
  | "hotel"
  | "itinerary"
  | "weather"
  | "currency"
  | "location"

export interface StructuredResult {
  type: StructuredResultType
  tool: string
  data: unknown
}

export interface Attachment {
  id: string
  name: string
  type: string
  size: number
  content: string
}

export interface ToolActivity {
  id: string
  label: string
  server: string
  status: ToolStatus
}

export interface QuickReplyOption {
  id: string
  label: string
  value: string
}

export interface QuickReplies {
  options: QuickReplyOption[]
  allowCustomAnswer?: boolean
  questionId?: string
  step?: number
  totalSteps?: number
  answeredValue?: string
}

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  createdAt: string
  attachments?: Pick<Attachment, "id" | "name" | "type" | "size">[]
  tools?: ToolActivity[]
  results?: StructuredResult[]
  quickReplies?: QuickReplies
}

export interface TripContext {
  destination: string | null
  dates: string | null
  travelers: string | null
  budget: string | null
  preferences: string[]
}

export interface Conversation {
  id: string
  title: string
  sessionId: string | null
  createdAt: string
  updatedAt: string
  messages: ChatMessage[]
  tripContext: TripContext
  pinned?: boolean
  planId?: string
}

export interface PlanFolder {
  id: string
  name: string
  createdAt: string
  updatedAt: string
}

export interface ServiceState {
  key: ServiceKey
  label: string
  status: ToolStatus
}

export interface RuntimeState {
  activity: string
  activeAgent: string
  backendOnline: boolean
  mcpServers: McpServerStatuses
  services: Record<ServiceKey, ServiceState>
}

export interface TripWeaverSettings {
  autoSave: boolean
  showToolActivity: boolean
}

export interface AccountUser {
  id: string
  email: string
  name: string
  created_at: string
}
