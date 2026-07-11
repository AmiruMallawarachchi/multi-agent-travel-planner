"""
mcp_servers/flight_server.py
Flight MCP Server for TripWeaver.

Exposes three MCP tools:
  - list_flights   : Browse all flights for a route and date.
  - search_flights : Filter flights by passengers, cabin class, and budget.
  - book_flight    : Confirm a flight reservation.

Data source: Realistic mock data (no external API required).
To plug in a real provider (Amadeus, Skyscanner, etc.) replace the
mock data and _fetch_* helpers below — agent code never changes.

Run standalone:
  python mcp_servers/flight_server.py

The TripWeaver agents connect to this server via MCP stdio transport.
"""

from __future__ import annotations
import json
import random
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("TripWeaver Flight Service")


# ─────────────────────────────────────────────────────────────
# Mock Flight Database
# ─────────────────────────────────────────────────────────────

_FLIGHTS: list[dict] = [
    {
        "id": "F001",
        "airline": "Emirates",
        "airline_code": "EK",
        "flight_number": "EK 205",
        "departure_time": "08:30",
        "arrival_time": "14:45",
        "duration": "6h 15m",
        "stops": 0,
        "stopover": None,
        "price_per_person": {
            "economy": 650,
            "premium_economy": 1100,
            "business": 3200,
            "first": 7500,
        },
        "available_seats": {"economy": 45, "premium_economy": 12, "business": 8, "first": 4},
        "baggage": "23kg included",
        "on_time_rating": "92%",
    },
    {
        "id": "F002",
        "airline": "British Airways",
        "airline_code": "BA",
        "flight_number": "BA 107",
        "departure_time": "11:00",
        "arrival_time": "18:30",
        "duration": "7h 30m",
        "stops": 1,
        "stopover": "Frankfurt (1h 20m layover)",
        "price_per_person": {
            "economy": 480,
            "premium_economy": 860,
            "business": 2400,
            "first": None,
        },
        "available_seats": {"economy": 120, "premium_economy": 24, "business": 14, "first": 0},
        "baggage": "23kg included",
        "on_time_rating": "85%",
    },
    {
        "id": "F003",
        "airline": "Qatar Airways",
        "airline_code": "QR",
        "flight_number": "QR 401",
        "departure_time": "22:15",
        "arrival_time": "07:20+1",
        "duration": "9h 05m",
        "stops": 0,
        "stopover": None,
        "price_per_person": {
            "economy": 890,
            "premium_economy": 1450,
            "business": 4100,
            "first": 9800,
        },
        "available_seats": {"economy": 30, "premium_economy": 18, "business": 10, "first": 6},
        "baggage": "30kg included",
        "on_time_rating": "95%",
    },
    {
        "id": "F004",
        "airline": "Lufthansa",
        "airline_code": "LH",
        "flight_number": "LH 512",
        "departure_time": "14:20",
        "arrival_time": "23:55",
        "duration": "9h 35m",
        "stops": 1,
        "stopover": "Munich (45m layover)",
        "price_per_person": {
            "economy": 520,
            "premium_economy": 980,
            "business": 2800,
            "first": None,
        },
        "available_seats": {"economy": 85, "premium_economy": 20, "business": 16, "first": 0},
        "baggage": "23kg included",
        "on_time_rating": "88%",
    },
    {
        "id": "F005",
        "airline": "Singapore Airlines",
        "airline_code": "SQ",
        "flight_number": "SQ 317",
        "departure_time": "01:30",
        "arrival_time": "12:00",
        "duration": "10h 30m",
        "stops": 0,
        "stopover": None,
        "price_per_person": {
            "economy": 780,
            "premium_economy": 1350,
            "business": 5200,
            "first": 12000,
        },
        "available_seats": {"economy": 60, "premium_economy": 28, "business": 12, "first": 6},
        "baggage": "30kg included",
        "on_time_rating": "96%",
    },
    {
        "id": "F006",
        "airline": "Turkish Airlines",
        "airline_code": "TK",
        "flight_number": "TK 1986",
        "departure_time": "06:45",
        "arrival_time": "17:10",
        "duration": "10h 25m",
        "stops": 1,
        "stopover": "Istanbul (1h 55m layover)",
        "price_per_person": {
            "economy": 410,
            "premium_economy": 750,
            "business": 2100,
            "first": None,
        },
        "available_seats": {"economy": 150, "premium_economy": 30, "business": 20, "first": 0},
        "baggage": "23kg included",
        "on_time_rating": "82%",
    },
]

_VALID_CABINS = {"economy", "premium_economy", "business", "first"}


def _format_flight(flight: dict, date: str, passengers: int, cabin: str) -> dict | None:
    """Add computed total price and filter out unavailable cabin classes."""
    cabin = cabin.lower().replace(" ", "_")
    if cabin not in _VALID_CABINS:
        cabin = "economy"

    price_per_person = flight["price_per_person"].get(cabin)
    seats = flight["available_seats"].get(cabin, 0)

    if price_per_person is None or seats < passengers:
        return None  # cabin not available or not enough seats

    return {
        "id": flight["id"],
        "airline": flight["airline"],
        "airline_code": flight["airline_code"],
        "flight_number": flight["flight_number"],
        "date": date,
        "departure_time": flight["departure_time"],
        "arrival_time": flight["arrival_time"],
        "duration": flight["duration"],
        "stops": flight["stops"],
        "stopover": flight["stopover"],
        "cabin_class": cabin.replace("_", " ").title(),
        "price_per_person_usd": price_per_person,
        "total_price_usd": round(price_per_person * passengers, 2),
        "passengers": passengers,
        "available_seats": seats,
        "baggage": flight["baggage"],
        "on_time_rating": flight["on_time_rating"],
        "currency": "USD",
    }


# ─────────────────────────────────────────────────────────────
# MCP Tools
# ─────────────────────────────────────────────────────────────

@mcp.tool()
def list_flights(origin: str, destination: str, date: str) -> str:
    """
    List all available flights for a route and travel date.

    Args:
        origin: Departure city or airport (e.g., "London")
        destination: Arrival city or airport (e.g., "Tokyo")
        date: Travel date in YYYY-MM-DD format

    Returns:
        JSON array of flight options with pricing for all cabin classes.
    """
    formatted = []
    for f in _FLIGHTS:
        entry = _format_flight(f, date, 1, "economy")
        if entry:
            # Include all cabin price options for browsing
            entry["all_cabin_prices"] = {
                k: v for k, v in f["price_per_person"].items() if v is not None
            }
            formatted.append(entry)

    result = {
        "origin": origin,
        "destination": destination,
        "date": date,
        "total_results": len(formatted),
        "flights": formatted,
    }
    return json.dumps(result, indent=2)


@mcp.tool()
def search_flights(
    origin: str,
    destination: str,
    date: str,
    passengers: int = 1,
    cabin_class: str = "economy",
    budget: float = 2000.0,
) -> str:
    """
    Search flights filtered by passengers, cabin class, and total budget.

    Args:
        origin: Departure city or airport (e.g., "New York")
        destination: Arrival city or airport (e.g., "Paris")
        date: Travel date in YYYY-MM-DD format
        passengers: Number of passengers (default 1)
        cabin_class: "economy", "premium_economy", "business", or "first" (default "economy")
        budget: Maximum total price in USD for all passengers (default 2000)

    Returns:
        JSON array of matching flights sorted by total price (ascending).
    """
    formatted = []
    for f in _FLIGHTS:
        entry = _format_flight(f, date, passengers, cabin_class)
        if entry and entry["total_price_usd"] <= budget:
            formatted.append(entry)

    # Sort by price ascending, then stops (direct first)
    formatted.sort(key=lambda f: (f["total_price_usd"], f["stops"]))

    result = {
        "origin": origin,
        "destination": destination,
        "date": date,
        "filters_applied": {
            "passengers": passengers,
            "cabin_class": cabin_class,
            "max_budget_usd": budget,
        },
        "total_results": len(formatted),
        "flights": formatted,
    }
    return json.dumps(result, indent=2)


@mcp.tool()
def book_flight(
    flight_id: str,
    passenger_name: str,
    origin: str,
    destination: str,
    date: str,
    passengers: int = 1,
    cabin_class: str = "economy",
) -> str:
    """
    Book a flight and return a booking confirmation.

    Args:
        flight_id: Flight ID from a previous list or search result (e.g., "F001")
        passenger_name: Full name of the primary passenger
        origin: Departure city
        destination: Arrival city
        date: Travel date in YYYY-MM-DD format
        passengers: Number of passengers (default 1)
        cabin_class: Cabin class (default "economy")

    Returns:
        JSON booking confirmation with confirmation_number and itinerary details.
    """
    flight = next((f for f in _FLIGHTS if f["id"] == flight_id), None)

    if flight is None:
        return json.dumps({
            "success": False,
            "error": f"No flight found with ID '{flight_id}'. Please use a valid flight ID from a search result.",
        })

    entry = _format_flight(flight, date, passengers, cabin_class)
    if entry is None:
        return json.dumps({
            "success": False,
            "error": f"Cabin class '{cabin_class}' is not available on flight {flight['flight_number']}, "
                     f"or there are not enough seats for {passengers} passenger(s).",
        })

    confirmation_number = f"TW-FLT-{random.randint(100000, 999999)}"

    return json.dumps({
        "success": True,
        "confirmation_number": confirmation_number,
        "status": "CONFIRMED",
        "flight": {
            "id": flight["id"],
            "airline": flight["airline"],
            "flight_number": flight["flight_number"],
            "departure_time": flight["departure_time"],
            "arrival_time": flight["arrival_time"],
            "duration": flight["duration"],
            "stops": flight["stops"],
        },
        "route": f"{origin} → {destination}",
        "date": date,
        "passenger_name": passenger_name,
        "passengers": passengers,
        "cabin_class": cabin_class.replace("_", " ").title(),
        "total_cost_usd": entry["total_price_usd"],
        "currency": "USD",
        "baggage": flight["baggage"],
        "message": f"Your flight {flight['flight_number']} on {date} is confirmed! Reference: {confirmation_number}",
    }, indent=2)


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
