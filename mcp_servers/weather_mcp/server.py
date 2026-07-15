"""FastMCP weather service backed by Open-Meteo."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from fastmcp import FastMCP
from open_meteo_client import (
    InvalidInputError,
    WeatherProviderError,
    get_weather_forecast as fetch_weather_forecast,
)
from starlette.requests import Request
from starlette.responses import JSONResponse

load_dotenv()

mcp = FastMCP("weather-mcp")


@mcp.custom_route("/health", methods=["GET"])
async def health(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "weather-mcp"})


async def _weather_result(**arguments: Any) -> dict[str, Any]:
    try:
        weather = await fetch_weather_forecast(**arguments)
        return {"ok": True, "weather": weather}
    except InvalidInputError as exc:
        return {"ok": False, "error": str(exc)}
    except WeatherProviderError as exc:
        return {"ok": False, "error": f"Weather service unavailable: {exc}"}


@mcp.tool()
async def get_current_weather(
    location: str,
    temperature_unit: str = "celsius",
    wind_speed_unit: str = "kmh",
    precipitation_unit: str = "mm",
) -> dict[str, Any]:
    """Get current weather for a city or place name."""
    result = await _weather_result(
        location=location,
        forecast_days=1,
        temperature_unit=temperature_unit,
        wind_speed_unit=wind_speed_unit,
        precipitation_unit=precipitation_unit,
    )
    if result.get("ok"):
        weather = result["weather"]
        result["weather"] = {
            "location": weather["location"],
            "timezone": weather["timezone"],
            "current": weather["current"],
            "source": weather["source"],
        }
    return result


@mcp.tool()
async def get_weather_forecast(
    location: str,
    forecast_days: int = 7,
    start_date: str | None = None,
    end_date: str | None = None,
    temperature_unit: str = "celsius",
    wind_speed_unit: str = "kmh",
    precipitation_unit: str = "mm",
) -> dict[str, Any]:
    """Get up to 16 days of current and daily weather for a place."""
    return await _weather_result(
        location=location,
        forecast_days=forecast_days,
        start_date=start_date,
        end_date=end_date,
        temperature_unit=temperature_unit,
        wind_speed_unit=wind_speed_unit,
        precipitation_unit=precipitation_unit,
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8004"))
    mcp.run(transport="http", host="0.0.0.0", port=port)
