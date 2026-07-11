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
from starlette.requests import Request
from starlette.responses import JSONResponse

load_dotenv()

from amadeus_client import (
    AmadeusError,
    InvalidInputError,
    book_flight_offer,
    list_flights as amadeus_list_flights,
    search_flight_offers,
)

mcp = FastMCP("flight-mcp")


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "flight-mcp"})


@mcp.tool()
async def list_flights(origin: str, destination: str) -> dict:
    """List flights operating on a route, as a lightweight overview.

    Args:
        origin: 3-letter IATA airport code, e.g. 'CMB'.
        destination: 3-letter IATA airport code, e.g. 'LHR'.
    """
    try:
        flights = await amadeus_list_flights(origin, destination)
        return {"ok": True, "flights": flights}
    except InvalidInputError as exc:
        return {"ok": False, "error": str(exc)}
    except AmadeusError as exc:
        return {"ok": False, "error": f"Flight service unavailable: {exc}"}


@mcp.tool()
async def search_flights(origin: str, destination: str, departure_date: str, adults: int = 1) -> dict:
    """Search priced, available flight offers for a route and date.

    Args:
        origin: 3-letter IATA airport code, e.g. 'CMB'.
        destination: 3-letter IATA airport code, e.g. 'LHR'.
        departure_date: 'YYYY-MM-DD'.
        adults: number of travellers (1-9).
    """
    try:
        offers = await search_flight_offers(origin, destination, departure_date, adults)
        return {"ok": True, "offers": offers}
    except InvalidInputError as exc:
        return {"ok": False, "error": str(exc)}
    except AmadeusError as exc:
        return {"ok": False, "error": f"Flight service unavailable: {exc}"}


@mcp.tool()
async def book_flight(offer_id: str, traveller_name: str) -> dict:
    """Book a specific flight offer returned by search_flights.

    Args:
        offer_id: the offer's id field from a prior search_flights result.
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
