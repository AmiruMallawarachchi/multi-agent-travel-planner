"""
mcp_servers/flight_mcp/server.py
MCP server exposing flight capabilities to the TripWeaver agent graph
(SRS section 9-E1): list_flights, search_flights, book_flight.

Run standalone:  python server.py
Docs:            MCP_SETUP.md at the repo root.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastmcp import FastMCP
from serpapi_client import (
    InvalidInputError,
    SerpApiError,
    book_flight_offer,
    list_flights as list_provider_flights,
    search_flight_offers,
)
from starlette.requests import Request
from starlette.responses import JSONResponse

load_dotenv()

mcp = FastMCP("flight-mcp")


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "flight-mcp"})


@mcp.tool()
async def list_flights(departure_id: str, arrival_id: str) -> dict:
    """List flights operating on a route, as a lightweight overview.

    Args:
        departure_id: 3-letter IATA airport code, e.g. 'CMB'.
        arrival_id: 3-letter IATA airport code, e.g. 'LHR'.
    """
    try:
        flights = await list_provider_flights(departure_id, arrival_id)
        return {"ok": True, "flights": flights}
    except InvalidInputError as exc:
        return {"ok": False, "error": str(exc)}
    except SerpApiError as exc:
        return {"ok": False, "error": f"Flight service unavailable: {exc}"}


@mcp.tool()
async def search_flights(
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    return_date: str | None = None,
    adults: int = 1,
    children: int = 0,
    travel_class: int = 1,
    currency: str = "USD",
    max_price: int | None = None,
) -> dict:
    """Search priced, available flight offers for a route and date.

    Args:
        departure_id: 3-letter IATA airport code, e.g. 'CMB'.
        arrival_id: 3-letter IATA airport code, e.g. 'LHR'.
        outbound_date: Outbound date in 'YYYY-MM-DD' format.
        return_date: Optional return date. Omit for a one-way search.
        adults: number of travellers (1-9).
        children: number of child travellers (0-9; maximum 9 total travellers).
        travel_class: 1 economy, 2 premium economy, 3 business, or 4 first.
        currency: 3-letter currency code, e.g. 'USD'.
        max_price: Optional maximum total ticket price.
    """
    try:
        offers = await search_flight_offers(
            departure_id=departure_id,
            arrival_id=arrival_id,
            outbound_date=outbound_date,
            return_date=return_date,
            adults=adults,
            children=children,
            travel_class=travel_class,
            currency=currency,
            max_price=max_price,
        )
        return {"ok": True, "offers": offers}
    except InvalidInputError as exc:
        return {"ok": False, "error": str(exc)}
    except SerpApiError as exc:
        return {"ok": False, "error": f"Flight service unavailable: {exc}"}


@mcp.tool()
async def book_flight(offer_id: str, traveller_name: str) -> dict:
    """Book a specific flight offer returned by search_flights.

    Args:
        offer_id: booking_token from a prior search_flights result.
        traveller_name: full name for the booking.
    """
    try:
        confirmation = await book_flight_offer(offer_id, traveller_name)
        return {"ok": True, "confirmation": confirmation}
    except InvalidInputError as exc:
        return {"ok": False, "error": str(exc)}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8002"))
    mcp.run(transport="http", host="0.0.0.0", port=port)
