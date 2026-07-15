import { describe, expect, it } from "vitest"

import { extractTripContext } from "./trip-context"

describe("extractTripContext", () => {
  it("extracts the common details from an itinerary request", () => {
    expect(
      extractTripContext(
        "Plan a 7 day trip to Tokyo for 2 people in December with a budget of $3000. I like sightseeing, food and culture.",
      ),
    ).toEqual({
      destination: "Tokyo",
      dates: "December",
      travelers: "2 people",
      budget: "$3000",
      preferences: ["Sightseeing", "Food", "Culture"],
    })
  })

  it("understands a flight-style request and keeps earlier context", () => {
    const previous = {
      destination: "Tokyo",
      dates: null,
      travelers: "2 adults",
      budget: null,
      preferences: ["Food"],
    }

    expect(
      extractTripContext(
        "Search flights from Colombo to London on 2026-09-01 for 1 adult",
        previous,
      ),
    ).toEqual({
      destination: "London",
      dates: "2026-09-01",
      travelers: "1 adult",
      budget: null,
      preferences: ["Food"],
    })
  })
})
