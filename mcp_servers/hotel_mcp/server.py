"""
mcp_servers/hotel_mcp/server.py
MCP server exposing hotel capabilities to the TripWeaver agent graph
(SRS section 9-E1): list_hotels, search_hotels, book_hotel.

Run standalone:  python server.py
Docs:            MCP_SETUP.md at the repo root.

Every tool below returns {"ok": bool, ...} rather than raising - MCP tool
errors surface to the calling agent as data it can reason about and relay
honestly to the traveller (SRS section 5: "must never silently swallow a
failed external call").
"""
from __future__ import annotations

import os

from fastmcp import FastMCP

from amadeus_client import AmadeusError, InvalidInputError, book_hotel_offer, list_hotels_by_city, search_hotel_offers

mcp = FastMCP("hotel-mcp")


@mcp.tool()
async def list_hotels(city_code: str) -> dict:
    """List hotels available in a city, before pricing or dates are known.

    Args:
        city_code: 3-letter IATA city code, e.g. 'PAR' for Paris, 'CMB' for Colombo.
    """
    try:
        hotels = await list_hotels_by_city(city_code)
        return {"ok": True, "hotels": hotels}
    except InvalidInputError as exc:
        return {"ok": False, "error": str(exc)}
    except AmadeusError as exc:
        return {"ok": False, "error": f"Hotel service unavailable: {exc}"}


@mcp.tool()
async def search_hotels(city_code: str, check_in: str, check_out: str, adults: int = 1) -> dict:
    """Search priced, available hotel offers.

    Args:
        city_code: 3-letter IATA city code, e.g. 'PAR'.
        check_in: check-in date, 'YYYY-MM-DD'.
        check_out: check-out date, 'YYYY-MM-DD'.
        adults: number of guests (1-9).
    """
    try:
        offers = await search_hotel_offers(city_code, check_in, check_out, adults)
        return {"ok": True, "offers": offers}
    except InvalidInputError as exc:
        return {"ok": False, "error": str(exc)}
    except AmadeusError as exc:
        return {"ok": False, "error": f"Hotel service unavailable: {exc}"}


@mcp.tool()
async def book_hotel(offer_id: str, guest_name: str) -> dict:
    """Book a specific hotel offer returned by search_hotels.

    Args:
        offer_id: the offer's id field from a prior search_hotels result.
        guest_name: full name for the reservation.
    """
    try:
        confirmation = await book_hotel_offer(offer_id, guest_name)
        return {"ok": True, "confirmation": confirmation}
    except InvalidInputError as exc:
        return {"ok": False, "error": str(exc)}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8001"))
    mcp.run(transport="http", host="0.0.0.0", port=port)
