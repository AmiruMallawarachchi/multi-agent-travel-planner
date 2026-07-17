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
  if (typeof body.detail === "string" && body.detail.trim()) return body.detail
  if (Array.isArray(body.detail) && body.detail.length > 0) {
    return "The account request was rejected. Check the form fields and try again."
  }
  return fallback
}
