import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import {
  ItineraryDetails,
  StructuredResultPreview,
} from "./structured-results"

describe("structured travel results", () => {
  it("renders flight and hotel provider results", () => {
    render(
      <>
        <StructuredResultPreview
          result={{
            type: "flight",
            tool: "search_flights",
            data: [
              {
                airline: "Emirates",
                flight_number: "EK 649",
                departure: { airport_code: "CMB", time: "02:50" },
                arrival: { airport_code: "DXB", time: "05:55" },
                price: 420,
                currency: "USD",
              },
            ],
          }}
        />
        <StructuredResultPreview
          result={{
            type: "hotel",
            tool: "search_hotels",
            data: [
              {
                name: "Harbour Hotel",
                overall_rating: 4.6,
                review_count: 820,
                price_per_night: 180,
                currency: "USD",
              },
            ],
          }}
        />
      </>,
    )

    expect(screen.getByText(/Emirates EK 649/)).toBeInTheDocument()
    expect(screen.getByText("Harbour Hotel")).toBeInTheDocument()
    expect(screen.getByText("820 reviews")).toBeInTheDocument()
  })

  it("renders weather, currency, and location results", () => {
    render(
      <>
        <StructuredResultPreview
          result={{
            type: "weather",
            tool: "get_weather_forecast",
            data: {
              location: { name: "Tokyo", country: "Japan" },
              current: {
                weather: "Partly cloudy",
                temperature: 24,
                units: { temperature: "°C" },
              },
              daily: [],
            },
          }}
        />
        <StructuredResultPreview
          result={{
            type: "currency",
            tool: "convert_currency",
            data: {
              from_currency: "USD",
              to_currency: "JPY",
              rate: 158.2,
              converted_amount: 15820,
              as_of: "2026-07-13",
            },
          }}
        />
        <StructuredResultPreview
          result={{
            type: "location",
            tool: "search_places",
            data: [
              {
                name: "Tokyo National Museum",
                category: "Museum",
                address: "Ueno Park",
                rating: 4.6,
                review_count: 1200,
                open_state: "Open now",
                coordinates: { latitude: 35.7188, longitude: 139.7765 },
              },
            ],
          }}
        />
      </>,
    )

    expect(screen.getByText("Tokyo, Japan")).toBeInTheDocument()
    expect(screen.getByText(/15,820 JPY/)).toBeInTheDocument()
    expect(screen.getByText("Tokyo National Museum")).toBeInTheDocument()
    expect(screen.getByText(/1,200 reviews/)).toBeInTheDocument()
    expect(screen.getByText("Open now")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Open Tokyo National Museum in maps" })).toHaveAttribute(
      "href",
      expect.stringContaining("35.7188"),
    )
  })

  it("renders structured itinerary days and activities", () => {
    render(
      <ItineraryDetails
        data={{
          destination: "Tokyo",
          start_date: "2026-12-10",
          end_date: "2026-12-11",
          duration_days: 2,
          travelers: 2,
          pace: "balanced",
          days: [
            {
              day_number: 1,
              date: "2026-12-10",
              title: "Day 1 in Tokyo",
              items: [
                {
                  name: "Tokyo National Museum",
                  time_slot: "morning",
                  duration_minutes: 120,
                  category: "Museum",
                  address: "Ueno Park",
                  source_url: "https://example.com/tokyo-museum",
                },
              ],
            },
          ],
        }}
      />,
    )

    expect(screen.getByText("Day 1 in Tokyo")).toBeInTheDocument()
    expect(screen.getByText("Tokyo National Museum")).toBeInTheDocument()
    expect(screen.getByText(/morning - 120 minutes/)).toBeInTheDocument()
    expect(screen.getByText("Museum")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Open details for Tokyo National Museum" })).toHaveAttribute(
      "href",
      "https://example.com/tokyo-museum",
    )
  })
})
