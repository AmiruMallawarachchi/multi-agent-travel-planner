"""FastMCP boundary for deterministic itinerary construction."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from fastmcp import FastMCP
from planner import InvalidInputError, create_itinerary_plan
from starlette.requests import Request
from starlette.responses import JSONResponse

load_dotenv()

mcp = FastMCP("itinerary-mcp")


@mcp.custom_route("/health", methods=["GET"])
async def health(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "itinerary-mcp"})


@mcp.tool()
async def create_itinerary(
    destination: str,
    start_date: str,
    end_date: str,
    travelers: int = 1,
    interests: list[str] | None = None,
    pace: str = "balanced",
    budget: float | None = None,
    budget_currency: str | None = None,
    activities: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a structured itinerary from trip details and optional place results."""
    try:
        itinerary = create_itinerary_plan(
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            travelers=travelers,
            interests=interests,
            pace=pace,
            budget=budget,
            budget_currency=budget_currency,
            activities=activities,
        )
        return {"ok": True, "itinerary": itinerary}
    except InvalidInputError as exc:
        return {"ok": False, "error": str(exc)}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8003"))
    mcp.run(transport="http", host="0.0.0.0", port=port)
