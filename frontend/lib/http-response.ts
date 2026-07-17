export type JsonObject = Record<string, unknown>

export async function readJsonObject(response: Response): Promise<JsonObject> {
  const text = await response.text()
  if (!text.trim()) return {}

  try {
    const value = JSON.parse(text) as unknown
    return value !== null && typeof value === "object" && !Array.isArray(value)
      ? (value as JsonObject)
      : {}
  } catch {
    return {}
  }
}

export function responseDetail(body: JsonObject, fallback: string) {
  return typeof body.detail === "string" && body.detail.trim() ? body.detail : fallback
}
