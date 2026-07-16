import type { PlanFolder } from "./types"

export const PLANS_STORAGE_KEY = "tripweaver.plans.v1"

function createId() {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function createPlanFolder(name: string, now = new Date(), id = createId()): PlanFolder {
  const timestamp = now.toISOString()
  return {
    id,
    name: name.trim().slice(0, 80),
    createdAt: timestamp,
    updatedAt: timestamp,
  }
}

function isPlanFolder(value: unknown): value is PlanFolder {
  if (!value || typeof value !== "object") return false
  const candidate = value as Partial<PlanFolder>
  return (
    typeof candidate.id === "string" &&
    candidate.id.length > 0 &&
    typeof candidate.name === "string" &&
    candidate.name.length > 0 &&
    typeof candidate.createdAt === "string" &&
    typeof candidate.updatedAt === "string"
  )
}

export function parseStoredPlans(raw: string | null): PlanFolder[] {
  if (!raw) return []
  try {
    const parsed: unknown = JSON.parse(raw)
    return Array.isArray(parsed) && parsed.every(isPlanFolder) ? parsed : []
  } catch {
    return []
  }
}
