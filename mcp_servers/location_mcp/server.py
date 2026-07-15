"""FastMCP location service backed by Open-Meteo and SerpApi."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from fastmcp import FastMCP
from location_client import (
    InvalidInputError,
    LocationProviderError,
    resolve_locations,
    search_places as search_provider_places,
)
from starlette.requests import Request
from starlette.responses import JSONResponse

load_dotenv()

mcp = FastMCP("location-mcp")


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "location-mcp"})


def _failure(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, InvalidInputError):
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "error": f"Location service unavailable: {exc}"}


@mcp.tool()
async def resolve_location(query: str, count: int = 5) -> dict[str, Any]:
    """Resolve a city or place name to coordinates and timezone metadata."""
    try:
        return {"ok": True, "locations": await resolve_locations(query, count=count)}
    except (InvalidInputError, LocationProviderError) as exc:
        return _failure(exc)


@mcp.tool()
async def search_places(
    query: str,
    near: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    zoom: int = 13,
) -> dict[str, Any]:
    """Search attractions, restaurants, and other local places."""
    try:
        places = await search_provider_places(
            query,
            near=near,
            latitude=latitude,
            longitude=longitude,
            zoom=zoom,
        )
        return {"ok": True, "places": places}
    except (InvalidInputError, LocationProviderError) as exc:
        return _failure(exc)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8006"))
    mcp.run(transport="http", host="0.0.0.0", port=port)
