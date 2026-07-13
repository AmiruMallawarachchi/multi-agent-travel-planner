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

from dotenv import load_dotenv
from fastmcp import FastMCP
from serpapi_client import (
    InvalidInputError,
    SerpApiError,
    book_hotel_offer,
    list_hotels as list_provider_hotels,
    search_hotel_properties,
)
from starlette.requests import Request
from starlette.responses import JSONResponse

load_dotenv()

mcp = FastMCP("hotel-mcp")


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "hotel-mcp"})


@mcp.tool()
async def list_hotels(destination: str) -> dict:
    """List hotels using a one-night stay beginning tomorrow.

    Args:
        destination: City, area, or complete hotel query, e.g. 'Paris'.
    """
    try:
        hotels = await list_provider_hotels(destination)
        return {"ok": True, "hotels": hotels}
    except InvalidInputError as exc:
        return {"ok": False, "error": str(exc)}
    except SerpApiError as exc:
        return {"ok": False, "error": f"Hotel service unavailable: {exc}"}


@mcp.tool()
async def search_hotels(
    destination: str,
    check_in_date: str,
    check_out_date: str,
    adults: int = 2,
    children: int = 0,
    currency: str = "USD",
    min_price: int | None = None,
    max_price: int | None = None,
    rating: int | None = None,
) -> dict:
    """Search priced, available hotel offers.

    Args:
        destination: City, area, or complete hotel query, e.g. 'Dubai Marina'.
        check_in_date: Check-in date in 'YYYY-MM-DD' format.
        check_out_date: Check-out date in 'YYYY-MM-DD' format.
        adults: Number of adult guests (1-10).
        children: Number of child guests (0-10; maximum 10 total guests).
        currency: 3-letter currency code, e.g. 'USD'.
        min_price: Optional minimum nightly price.
        max_price: Optional maximum nightly price.
        rating: Optional SerpApi rating filter: 7 (3.5+), 8 (4.0+), or 9 (4.5+).
    """
    try:
        offers = await search_hotel_properties(
            destination=destination,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            adults=adults,
            children=children,
            currency=currency,
            min_price=min_price,
            max_price=max_price,
            rating=rating,
        )
        return {"ok": True, "offers": offers}
    except InvalidInputError as exc:
        return {"ok": False, "error": str(exc)}
    except SerpApiError as exc:
        return {"ok": False, "error": f"Hotel service unavailable: {exc}"}


@mcp.tool()
async def book_hotel(offer_id: str, guest_name: str) -> dict:
    """Book a specific hotel offer returned by search_hotels.

    Args:
        offer_id: property_token from a prior search_hotels result.
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
