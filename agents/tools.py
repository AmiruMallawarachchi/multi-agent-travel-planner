"""
agents/tools.py
MCP client helpers + LangChain @tool definitions used by Hotel and Flight agents.

Architecture
------------
Each `@tool` function is a LangChain tool that:
  1. Calls the relevant MCP server via stdio transport.
  2. Returns the tool result as a string for the LLM to reason over.
  3. Catches ALL exceptions and returns a user-friendly error string
     so the agent can handle failures gracefully (never crashes).

The agents bind these tools to their LLM via `llm.bind_tools(...)`.
The MCP servers run as separate subprocesses (stdio transport).
"""

from __future__ import annotations
import sys
import os
import json
from pathlib import Path
from langchain_core.tools import tool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Path to MCP server scripts — resolved relative to this file
_BASE_DIR = Path(__file__).resolve().parent.parent
_HOTEL_SERVER = str(_BASE_DIR / "mcp_servers" / "hotel_server.py")
_FLIGHT_SERVER = str(_BASE_DIR / "mcp_servers" / "flight_server.py")


# ─────────────────────────────────────────────────────────────
# Low-level MCP client
# ─────────────────────────────────────────────────────────────

async def _call_mcp_server(server_script: str, tool_name: str, params: dict) -> str:
    """
    Spin up an MCP server subprocess, call one tool, return the text result.

    Uses stdio transport — each call starts the server, runs the tool,
    and the context manager handles clean shutdown.
    """
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        env={**os.environ},
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, params)
            if result.content:
                return result.content[0].text
            return json.dumps({"message": "No results returned by the service."})


async def call_hotel_mcp(tool_name: str, **params) -> str:
    """Call any tool on the Hotel MCP server."""
    return await _call_mcp_server(_HOTEL_SERVER, tool_name, params)


async def call_flight_mcp(tool_name: str, **params) -> str:
    """Call any tool on the Flight MCP server."""
    return await _call_mcp_server(_FLIGHT_SERVER, tool_name, params)


# ─────────────────────────────────────────────────────────────
# Hotel LangChain Tools
# ─────────────────────────────────────────────────────────────

@tool
async def list_hotels(city: str, check_in: str, check_out: str) -> str:
    """
    List all available hotels in a city for given dates.
    Use this when the traveller wants to browse options without specific filters.

    Args:
        city: Destination city (e.g., "Paris")
        check_in: Check-in date in YYYY-MM-DD format
        check_out: Check-out date in YYYY-MM-DD format
    """
    try:
        return await call_hotel_mcp("list_hotels", city=city, check_in=check_in, check_out=check_out)
    except Exception as e:
        return json.dumps({"error": f"Hotel service is temporarily unavailable: {str(e)}"})


@tool
async def search_hotels(
    city: str,
    check_in: str,
    check_out: str,
    budget: float = 500.0,
    guests: int = 1,
    stars: int = 3,
) -> str:
    """
    Search for hotels matching specific criteria.
    Use this when the traveller specifies a budget, guest count, or star rating.

    Args:
        city: Destination city (e.g., "Tokyo")
        check_in: Check-in date in YYYY-MM-DD format
        check_out: Check-out date in YYYY-MM-DD format
        budget: Maximum price per night in USD (default 500)
        guests: Number of guests (default 1)
        stars: Minimum star rating 1-5 (default 3)
    """
    try:
        return await call_hotel_mcp(
            "search_hotels",
            city=city, check_in=check_in, check_out=check_out,
            budget=budget, guests=guests, stars=stars,
        )
    except Exception as e:
        return json.dumps({"error": f"Hotel search is temporarily unavailable: {str(e)}"})


@tool
async def book_hotel(
    hotel_id: str,
    guest_name: str,
    check_in: str,
    check_out: str,
    guests: int = 1,
) -> str:
    """
    Book a hotel room and return a booking confirmation.
    Only call this when the traveller explicitly asks to book/reserve a hotel.

    Args:
        hotel_id: The hotel ID from a previous list or search result
        guest_name: Full name of the primary guest
        check_in: Check-in date in YYYY-MM-DD format
        check_out: Check-out date in YYYY-MM-DD format
        guests: Number of guests (default 1)
    """
    try:
        return await call_hotel_mcp(
            "book_hotel",
            hotel_id=hotel_id, guest_name=guest_name,
            check_in=check_in, check_out=check_out, guests=guests,
        )
    except Exception as e:
        return json.dumps({"error": f"Hotel booking is temporarily unavailable: {str(e)}"})


# ─────────────────────────────────────────────────────────────
# Flight LangChain Tools
# ─────────────────────────────────────────────────────────────

@tool
async def list_flights(origin: str, destination: str, date: str) -> str:
    """
    List all available flights between two cities on a given date.
    Use this when the traveller wants to browse options without specific filters.

    Args:
        origin: Departure city or airport (e.g., "London")
        destination: Arrival city or airport (e.g., "Tokyo")
        date: Travel date in YYYY-MM-DD format
    """
    try:
        return await call_flight_mcp("list_flights", origin=origin, destination=destination, date=date)
    except Exception as e:
        return json.dumps({"error": f"Flight service is temporarily unavailable: {str(e)}"})


@tool
async def search_flights(
    origin: str,
    destination: str,
    date: str,
    passengers: int = 1,
    cabin_class: str = "economy",
    budget: float = 2000.0,
) -> str:
    """
    Search for flights with specific filters.
    Use this when the traveller specifies passengers, cabin class, or a budget.

    Args:
        origin: Departure city or airport (e.g., "New York")
        destination: Arrival city or airport (e.g., "Paris")
        date: Travel date in YYYY-MM-DD format
        passengers: Number of passengers (default 1)
        cabin_class: "economy", "premium_economy", "business", or "first" (default "economy")
        budget: Maximum total price in USD (default 2000)
    """
    try:
        return await call_flight_mcp(
            "search_flights",
            origin=origin, destination=destination, date=date,
            passengers=passengers, cabin_class=cabin_class, budget=budget,
        )
    except Exception as e:
        return json.dumps({"error": f"Flight search is temporarily unavailable: {str(e)}"})


@tool
async def book_flight(
    flight_id: str,
    passenger_name: str,
    origin: str,
    destination: str,
    date: str,
) -> str:
    """
    Book a flight and return a booking confirmation.
    Only call this when the traveller explicitly asks to book/reserve a flight.

    Args:
        flight_id: The flight ID from a previous list or search result
        passenger_name: Full name of the primary passenger
        origin: Departure city
        destination: Arrival city
        date: Travel date in YYYY-MM-DD format
    """
    try:
        return await call_flight_mcp(
            "book_flight",
            flight_id=flight_id, passenger_name=passenger_name,
            origin=origin, destination=destination, date=date,
        )
    except Exception as e:
        return json.dumps({"error": f"Flight booking is temporarily unavailable: {str(e)}"})


# ─────────────────────────────────────────────────────────────
# Tool groups — imported by nodes.py
# ─────────────────────────────────────────────────────────────

HOTEL_TOOLS = [list_hotels, search_hotels, book_hotel]
FLIGHT_TOOLS = [list_flights, search_flights, book_flight]
