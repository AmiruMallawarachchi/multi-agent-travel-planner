import { describe, expect, it } from "vitest"

import { createPlanFolder, parseStoredPlans } from "./plans"

describe("plan folders", () => {
  it("creates a normalized folder", () => {
    expect(
      createPlanFolder("  Japan 2027  ", new Date("2026-07-16T08:00:00.000Z"), "japan"),
    ).toEqual({
      id: "japan",
      name: "Japan 2027",
      createdAt: "2026-07-16T08:00:00.000Z",
      updatedAt: "2026-07-16T08:00:00.000Z",
    })
  })

  it("accepts valid storage and rejects malformed data", () => {
    const plan = createPlanFolder("Europe", new Date("2026-07-16T08:00:00.000Z"), "europe")
    expect(parseStoredPlans(JSON.stringify([plan]))).toEqual([plan])
    expect(parseStoredPlans(JSON.stringify([{ id: "broken" }]))).toEqual([])
    expect(parseStoredPlans("not-json")).toEqual([])
  })
})
