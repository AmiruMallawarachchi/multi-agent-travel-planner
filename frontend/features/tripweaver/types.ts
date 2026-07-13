export type MessageRole = "assistant" | "user"

export type ToolStatus = "idle" | "running" | "completed" | "failed" | "offline" | "unavailable"

export type ServiceKey = "flight" | "hotel" | "itinerary" | "weather" | "currency" | "location"

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

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  createdAt: string
  attachments?: Pick<Attachment, "id" | "name" | "type" | "size">[]
  tools?: ToolActivity[]
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
  services: Record<ServiceKey, ServiceState>
}

export interface TripWeaverSettings {
  autoSave: boolean
  showToolActivity: boolean
}
