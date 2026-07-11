"""
mcp_servers/hotel_server.py
Hotel MCP Server for TripWeaver.

Exposes three MCP tools:
  - list_hotels   : Browse all hotels in a city for given dates.
  - search_hotels : Filter hotels by budget, guests, and star rating.
  - book_hotel    : Confirm a hotel reservation.

Data source: Realistic mock data (no external API required).
To plug in a real provider (Booking.com, Amadeus, etc.) replace the
_fetch_* helpers below — agent code never changes.

Run standalone:
  python mcp_servers/hotel_server.py

The TripWeaver agents connect to this server via MCP stdio transport.
"""

from __future__ import annotations
import json
import random
import sys
from datetime import date, datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("TripWeaver Hotel Service")


# ─────────────────────────────────────────────────────────────
# Mock Hotel Database
# ─────────────────────────────────────────────────────────────

_HOTELS: list[dict] = [
    {
        "id": "H001",
        "name": "The Grand Palace Hotel",
        "stars": 5,
        "price_per_night": 320,
        "rating": 4.9,
        "review_count": 3842,
        "location": "City Centre",
        "address": "1 Royal Boulevard",
        "amenities": ["Outdoor Pool", "Spa", "Michelin Restaurant", "Rooftop Bar", "WiFi", "Concierge", "Valet Parking"],
        "free_cancellation": True,
        "breakfast_included": True,
        "room_types": ["Deluxe Room", "Junior Suite", "Penthouse Suite"],
        "max_guests": 4,
    },
    {
        "id": "H002",
        "name": "Boutique Stays",
        "stars": 4,
        "price_per_night": 155,
        "rating": 4.7,
        "review_count": 1250,
        "location": "Arts District",
        "address": "27 Gallery Lane",
        "amenities": ["Rooftop Terrace", "Bar", "WiFi", "Fitness Centre", "Room Service"],
        "free_cancellation": True,
        "breakfast_included": False,
        "room_types": ["Standard Room", "Superior Room", "Studio Suite"],
        "max_guests": 2,
    },
    {
        "id": "H003",
        "name": "Comfort Inn & Suites",
        "stars": 3,
        "price_per_night": 89,
        "rating": 4.2,
        "review_count": 5610,
        "location": "Downtown",
        "address": "88 Main Street",
        "amenities": ["WiFi", "Parking", "Breakfast Buffet", "24h Front Desk"],
        "free_cancellation": False,
        "breakfast_included": True,
        "room_types": ["Standard Room", "Family Room"],
        "max_guests": 4,
    },
    {
        "id": "H004",
        "name": "Luxury Harbour Suites",
        "stars": 5,
        "price_per_night": 485,
        "rating": 4.8,
        "review_count": 2100,
        "location": "Waterfront",
        "address": "3 Marina Promenade",
        "amenities": ["Infinity Pool", "Private Beach", "Spa", "Butler Service", "WiFi", "3 Restaurants", "Yacht Charter"],
        "free_cancellation": True,
        "breakfast_included": True,
        "room_types": ["Harbour View Room", "Sea Suite", "Presidential Suite"],
        "max_guests": 6,
    },
    {
        "id": "H005",
        "name": "Budget Traveler's Lodge",
        "stars": 2,
        "price_per_night": 48,
        "rating": 3.9,
        "review_count": 4300,
        "location": "Near Airport",
        "address": "12 Terminal Road",
        "amenities": ["WiFi", "Shared Kitchen", "Lockers", "24h Reception"],
        "free_cancellation": True,
        "breakfast_included": False,
        "room_types": ["Private Room", "Dormitory (4-bed)", "Dormitory (8-bed)"],
        "max_guests": 2,
    },
    {
        "id": "H006",
        "name": "Radisson Heritage",
        "stars": 4,
        "price_per_night": 210,
        "rating": 4.5,
        "review_count": 1870,
        "location": "Historic Quarter",
        "address": "55 Heritage Square",
        "amenities": ["Indoor Pool", "Spa", "Restaurant", "Bar", "WiFi", "Fitness Centre", "Meeting Rooms"],
        "free_cancellation": False,
        "breakfast_included": True,
        "room_types": ["Classic Room", "Executive Room", "Suite"],
        "max_guests": 3,
    },
]


def _num_nights(check_in: str, check_out: str) -> int:
    """Calculate number of nights between two date strings."""
    try:
        d1 = date.fromisoformat(check_in)
        d2 = date.fromisoformat(check_out)
        nights = (d2 - d1).days
        return max(1, nights)
    except ValueError:
        return 1


def _format_hotel(hotel: dict, check_in: str, check_out: str) -> dict:
    """Add computed fields (total price, nights) to a hotel record."""
    nights = _num_nights(check_in, check_out)
    return {
        **hotel,
        "check_in": check_in,
        "check_out": check_out,
        "nights": nights,
        "total_price": round(hotel["price_per_night"] * nights, 2),
        "currency": "USD",
    }


# ─────────────────────────────────────────────────────────────
# MCP Tools
# ─────────────────────────────────────────────────────────────

@mcp.tool()
def list_hotels(city: str, check_in: str, check_out: str) -> str:
    """
    List all available hotels for a destination and date range.

    Args:
        city: Destination city name (e.g., "Paris")
        check_in: Check-in date in YYYY-MM-DD format
        check_out: Check-out date in YYYY-MM-DD format

    Returns:
        JSON array of hotel objects with pricing and amenities.
    """
    formatted = [_format_hotel(h, check_in, check_out) for h in _HOTELS]
    result = {
        "city": city,
        "check_in": check_in,
        "check_out": check_out,
        "total_results": len(formatted),
        "hotels": formatted,
    }
    return json.dumps(result, indent=2)


@mcp.tool()
def search_hotels(
    city: str,
    check_in: str,
    check_out: str,
    budget: float = 500.0,
    guests: int = 1,
    stars: int = 3,
) -> str:
    """
    Search hotels filtered by budget (per night), guest count, and minimum star rating.

    Args:
        city: Destination city name
        check_in: Check-in date in YYYY-MM-DD format
        check_out: Check-out date in YYYY-MM-DD format
        budget: Maximum price per night in USD (default 500)
        guests: Number of guests (default 1)
        stars: Minimum star rating 1-5 (default 3)

    Returns:
        JSON array of matching hotels sorted by star rating (descending).
    """
    filtered = [
        h for h in _HOTELS
        if h["price_per_night"] <= budget
        and h["stars"] >= stars
        and h["max_guests"] >= guests
    ]
    # Sort by stars desc, then rating desc
    filtered.sort(key=lambda h: (h["stars"], h["rating"]), reverse=True)
    formatted = [_format_hotel(h, check_in, check_out) for h in filtered]

    result = {
        "city": city,
        "check_in": check_in,
        "check_out": check_out,
        "filters_applied": {
            "max_budget_per_night": budget,
            "min_stars": stars,
            "guests": guests,
        },
        "total_results": len(formatted),
        "hotels": formatted,
    }
    return json.dumps(result, indent=2)


@mcp.tool()
def book_hotel(
    hotel_id: str,
    guest_name: str,
    check_in: str,
    check_out: str,
    guests: int = 1,
) -> str:
    """
    Book a hotel and return a confirmation with a booking reference number.

    Args:
        hotel_id: Hotel ID from a previous list or search result (e.g., "H001")
        guest_name: Full name of the primary guest
        check_in: Check-in date in YYYY-MM-DD format
        check_out: Check-out date in YYYY-MM-DD format
        guests: Number of guests (default 1)

    Returns:
        JSON booking confirmation with confirmation_number and booking details.
    """
    hotel = next((h for h in _HOTELS if h["id"] == hotel_id), None)

    if hotel is None:
        return json.dumps({
            "success": False,
            "error": f"No hotel found with ID '{hotel_id}'. Please use a valid hotel ID from a search result.",
        })

    if hotel["max_guests"] < guests:
        return json.dumps({
            "success": False,
            "error": f"{hotel['name']} accommodates a maximum of {hotel['max_guests']} guests.",
        })

    nights = _num_nights(check_in, check_out)
    total = round(hotel["price_per_night"] * nights, 2)
    confirmation_number = f"TW-HTL-{random.randint(100000, 999999)}"

    return json.dumps({
        "success": True,
        "confirmation_number": confirmation_number,
        "status": "CONFIRMED",
        "hotel": {
            "id": hotel["id"],
            "name": hotel["name"],
            "stars": hotel["stars"],
            "address": hotel["address"],
            "location": hotel["location"],
        },
        "guest_name": guest_name,
        "check_in": check_in,
        "check_out": check_out,
        "nights": nights,
        "guests": guests,
        "price_per_night_usd": hotel["price_per_night"],
        "total_cost_usd": total,
        "currency": "USD",
        "free_cancellation": hotel["free_cancellation"],
        "message": f"Your booking at {hotel['name']} is confirmed! Reference: {confirmation_number}",
    }, indent=2)


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
