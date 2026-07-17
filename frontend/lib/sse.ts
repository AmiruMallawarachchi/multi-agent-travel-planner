export type StreamEvent =
  | { type: "session"; session_id: string }
  | { type: "status"; state: string; node?: string }
  | { type: "tool"; status: string; tool: string }
  | {
      type: "result"
      result_type: "flight" | "hotel" | "itinerary" | "weather" | "currency" | "location"
      tool: string
      data: unknown
    }
  | { type: "token"; content: string }
  | {
      type: "quick_replies"
      options: { id: string; label: string; value: string }[]
      allow_custom_answer?: boolean
      question_id?: string
      step?: number
      total_steps?: number
    }
  | { type: "error"; message: string }
  | { type: "done" }

export function parseSseChunk(buffer: string) {
  const events: StreamEvent[] = []
  const parts = buffer.split("\n\n")
  const remainder = parts.pop() ?? ""

  for (const part of parts) {
    const line = part
      .split("\n")
      .map((value) => value.trim())
      .find((value) => value.startsWith("data: "))

    if (!line) {
      continue
    }

    events.push(JSON.parse(line.slice(6)) as StreamEvent)
  }

  return { events, remainder }
}
