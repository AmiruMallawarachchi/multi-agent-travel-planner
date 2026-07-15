"""Async Open-Meteo geocoding and weather adapter."""

from __future__ import annotations

import os
from datetime import date
from typing import Any

import httpx

DEFAULT_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
DEFAULT_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=10.0, pool=5.0)
MAX_FORECAST_DAYS = 16

_TEMPERATURE_UNITS = {"celsius", "fahrenheit"}
_WIND_SPEED_UNITS = {"kmh", "ms", "mph", "kn"}
_PRECIPITATION_UNITS = {"mm", "inch"}

_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherProviderError(RuntimeError):
    """Open-Meteo transport or response failure."""


class LocationNotFoundError(WeatherProviderError):
    """The geocoder returned no matching location."""


class InvalidInputError(ValueError):
    """Weather input failed validation before a provider request."""


class OpenMeteoClient:
    def __init__(
        self,
        *,
        geocoding_url: str | None = None,
        forecast_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.geocoding_url = (
            geocoding_url
            or os.getenv("OPEN_METEO_GEOCODING_URL")
            or DEFAULT_GEOCODING_URL
        ).strip()
        self.forecast_url = (
            forecast_url or os.getenv("OPEN_METEO_FORECAST_URL") or DEFAULT_FORECAST_URL
        ).strip()
        self.transport = transport

    async def get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT, transport=self.transport
            ) as client:
                response = await client.get(url, params=params)
        except httpx.TimeoutException:
            raise WeatherProviderError("Weather provider request timed out") from None
        except httpx.RequestError:
            raise WeatherProviderError("Weather provider request failed") from None

        if response.status_code >= 400:
            raise WeatherProviderError(
                f"Weather provider returned HTTP {response.status_code}"
            )
        try:
            payload = response.json()
        except ValueError:
            raise WeatherProviderError(
                "Weather provider returned invalid JSON"
            ) from None
        if not isinstance(payload, dict):
            raise WeatherProviderError(
                "Weather provider returned an unexpected response"
            )
        return payload


def _text(label: str, value: Any, maximum: int = 120) -> str:
    normalized = " ".join(str(value or "").split())
    if not normalized:
        raise InvalidInputError(f"{label} is required")
    if len(normalized) > maximum:
        raise InvalidInputError(f"{label} must be {maximum} characters or fewer")
    return normalized


def _integer(label: str, value: int, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        raise InvalidInputError(f"{label} must be between {minimum} and {maximum}")
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        raise InvalidInputError(
            f"{label} must be between {minimum} and {maximum}"
        ) from None
    if isinstance(value, float) and not value.is_integer():
        raise InvalidInputError(f"{label} must be between {minimum} and {maximum}")
    if not minimum <= normalized <= maximum:
        raise InvalidInputError(f"{label} must be between {minimum} and {maximum}")
    return normalized


def _calendar_date(label: str, value: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise InvalidInputError(
            f"{label} must be a valid calendar date in YYYY-MM-DD format"
        ) from None


def _date_range(
    start_date: str | None, end_date: str | None
) -> tuple[date, date] | None:
    if start_date is None and end_date is None:
        return None
    if not start_date or not end_date:
        raise InvalidInputError("start_date and end_date must be provided together")
    start = _calendar_date("start_date", start_date)
    end = _calendar_date("end_date", end_date)
    if end < start:
        raise InvalidInputError("end_date must be on or after start_date")
    if (end - start).days + 1 > MAX_FORECAST_DAYS:
        raise InvalidInputError(
            f"weather date range must not exceed {MAX_FORECAST_DAYS} days"
        )
    return start, end


def _unit(label: str, value: str, allowed: set[str]) -> str:
    normalized = str(value or "").strip().casefold()
    if normalized not in allowed:
        raise InvalidInputError(f"{label} must be one of {', '.join(sorted(allowed))}")
    return normalized


def _weather_description(value: Any) -> str:
    try:
        code = int(value)
    except (TypeError, ValueError):
        return "Unknown"
    return _WEATHER_CODES.get(code, "Unknown")


def _normalize_location(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": raw.get("name"),
        "country": raw.get("country"),
        "country_code": raw.get("country_code"),
        "region": raw.get("admin1"),
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "timezone": raw.get("timezone"),
    }


async def _resolve_location(location: str, client: OpenMeteoClient) -> dict[str, Any]:
    payload = await client.get_json(
        client.geocoding_url,
        {"name": location, "count": 1, "language": "en", "format": "json"},
    )
    results = payload.get("results")
    if not isinstance(results, list) or not results or not isinstance(results[0], dict):
        raise LocationNotFoundError(f"No location found for '{location}'")
    normalized = _normalize_location(results[0])
    if normalized["latitude"] is None or normalized["longitude"] is None:
        raise WeatherProviderError("Geocoding provider omitted coordinates")
    return normalized


def _value_at(values: Any, index: int) -> Any:
    return values[index] if isinstance(values, list) and index < len(values) else None


def _normalize_current(payload: dict[str, Any]) -> dict[str, Any]:
    current = payload.get("current")
    current = current if isinstance(current, dict) else {}
    units = payload.get("current_units")
    units = units if isinstance(units, dict) else {}
    code = current.get("weather_code")
    return {
        "observed_at": current.get("time"),
        "temperature": current.get("temperature_2m"),
        "apparent_temperature": current.get("apparent_temperature"),
        "precipitation": current.get("precipitation"),
        "weather_code": code,
        "weather": _weather_description(code),
        "cloud_cover": current.get("cloud_cover"),
        "wind_speed": current.get("wind_speed_10m"),
        "units": {
            "temperature": units.get("temperature_2m"),
            "apparent_temperature": units.get("apparent_temperature"),
            "precipitation": units.get("precipitation"),
            "wind_speed": units.get("wind_speed_10m"),
        },
    }


def _normalize_daily(payload: dict[str, Any]) -> list[dict[str, Any]]:
    daily = payload.get("daily")
    if not isinstance(daily, dict) or not isinstance(daily.get("time"), list):
        return []
    units = payload.get("daily_units")
    units = units if isinstance(units, dict) else {}
    results: list[dict[str, Any]] = []
    for index, day_value in enumerate(daily["time"]):
        code = _value_at(daily.get("weather_code"), index)
        results.append(
            {
                "date": day_value,
                "weather_code": code,
                "weather": _weather_description(code),
                "temperature_max": _value_at(daily.get("temperature_2m_max"), index),
                "temperature_min": _value_at(daily.get("temperature_2m_min"), index),
                "precipitation_probability_max": _value_at(
                    daily.get("precipitation_probability_max"), index
                ),
                "sunrise": _value_at(daily.get("sunrise"), index),
                "sunset": _value_at(daily.get("sunset"), index),
                "units": {
                    "temperature_max": units.get("temperature_2m_max"),
                    "temperature_min": units.get("temperature_2m_min"),
                    "precipitation_probability_max": units.get(
                        "precipitation_probability_max"
                    ),
                },
            }
        )
    return results


async def get_weather_forecast(
    location: str,
    forecast_days: int = 7,
    start_date: str | None = None,
    end_date: str | None = None,
    temperature_unit: str = "celsius",
    wind_speed_unit: str = "kmh",
    precipitation_unit: str = "mm",
    *,
    client: OpenMeteoClient | None = None,
) -> dict[str, Any]:
    """Resolve a location and return normalized current and daily weather."""
    location = _text("location", location)
    forecast_days = _integer("forecast_days", forecast_days, 1, MAX_FORECAST_DAYS)
    requested_range = _date_range(start_date, end_date)
    temperature_unit = _unit("temperature_unit", temperature_unit, _TEMPERATURE_UNITS)
    wind_speed_unit = _unit("wind_speed_unit", wind_speed_unit, _WIND_SPEED_UNITS)
    precipitation_unit = _unit(
        "precipitation_unit", precipitation_unit, _PRECIPITATION_UNITS
    )

    provider = client or OpenMeteoClient()
    resolved = await _resolve_location(location, provider)
    params: dict[str, Any] = {
        "latitude": resolved["latitude"],
        "longitude": resolved["longitude"],
        "timezone": "auto",
        "current": (
            "temperature_2m,apparent_temperature,precipitation,weather_code,"
            "cloud_cover,wind_speed_10m"
        ),
        "daily": (
            "weather_code,temperature_2m_max,temperature_2m_min,"
            "precipitation_probability_max,sunrise,sunset"
        ),
        "temperature_unit": temperature_unit,
        "wind_speed_unit": wind_speed_unit,
        "precipitation_unit": precipitation_unit,
    }
    if requested_range:
        params["start_date"] = requested_range[0].isoformat()
        params["end_date"] = requested_range[1].isoformat()
    else:
        params["forecast_days"] = forecast_days

    payload = await provider.get_json(provider.forecast_url, params)
    return {
        "location": resolved,
        "timezone": payload.get("timezone") or resolved.get("timezone"),
        "current": _normalize_current(payload),
        "daily": _normalize_daily(payload),
        "source": "Open-Meteo",
    }
