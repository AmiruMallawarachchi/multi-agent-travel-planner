"""Async geocoding and place-search adapter."""

from __future__ import annotations

import math
import os
from typing import Any

import httpx

DEFAULT_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
DEFAULT_SERPAPI_URL = "https://serpapi.com/search.json"
REQUEST_TIMEOUT = httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0)


class LocationProviderError(RuntimeError):
    """Geocoding or place-search provider failure."""


class LocationNotFoundError(LocationProviderError):
    """No location matched a requested place name."""


class InvalidInputError(ValueError):
    """Location input failed validation before a provider request."""


class LocationClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        geocoding_url: str | None = None,
        serpapi_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        configured_key = (
            api_key if api_key is not None else os.getenv("SERPAPI_API_KEY", "")
        )
        self.api_key = configured_key.strip()
        self.geocoding_url = (
            geocoding_url
            or os.getenv("OPEN_METEO_GEOCODING_URL")
            or DEFAULT_GEOCODING_URL
        ).strip()
        self.serpapi_url = (
            serpapi_url or os.getenv("SERPAPI_BASE_URL") or DEFAULT_SERPAPI_URL
        ).strip()
        self.transport = transport

    def redact(self, message: str) -> str:
        if not self.api_key:
            return message
        return message.replace(self.api_key, "[redacted]")

    async def get_json(
        self, url: str, params: dict[str, Any], *, provider: str
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT, transport=self.transport
            ) as client:
                response = await client.get(url, params=params)
        except httpx.TimeoutException:
            raise LocationProviderError(f"{provider} request timed out") from None
        except httpx.RequestError:
            raise LocationProviderError(f"{provider} request failed") from None

        if response.status_code >= 400:
            detail = _provider_detail(response)
            suffix = f": {self.redact(detail)}" if detail else ""
            raise LocationProviderError(
                f"{provider} returned HTTP {response.status_code}{suffix}"
            )
        try:
            payload = response.json()
        except ValueError:
            raise LocationProviderError(f"{provider} returned invalid JSON") from None
        if not isinstance(payload, dict):
            raise LocationProviderError(f"{provider} returned an unexpected response")
        error = payload.get("error")
        if error:
            raise LocationProviderError(f"{provider} error: {self.redact(str(error))}")
        return payload


def _provider_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return ""
    if isinstance(payload, dict) and payload.get("error"):
        return str(payload["error"])
    return ""


def _text(label: str, value: Any, maximum: int = 160) -> str:
    normalized = " ".join(str(value or "").split())
    if not normalized:
        raise InvalidInputError(f"{label} is required")
    if len(normalized) > maximum:
        raise InvalidInputError(f"{label} must be {maximum} characters or fewer")
    return normalized


def _integer(label: str, value: Any, minimum: int, maximum: int) -> int:
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


def _coordinate(label: str, value: Any, minimum: float, maximum: float) -> float:
    if isinstance(value, bool):
        raise InvalidInputError(f"{label} must be between {minimum:g} and {maximum:g}")
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        raise InvalidInputError(
            f"{label} must be between {minimum:g} and {maximum:g}"
        ) from None
    if not math.isfinite(normalized) or not minimum <= normalized <= maximum:
        raise InvalidInputError(f"{label} must be between {minimum:g} and {maximum:g}")
    return normalized


def _normalize_location(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": raw.get("name"),
        "country": raw.get("country"),
        "country_code": raw.get("country_code"),
        "region": raw.get("admin1"),
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "timezone": raw.get("timezone"),
        "elevation_meters": raw.get("elevation"),
        "population": raw.get("population"),
    }


def _normalize_place(raw: dict[str, Any]) -> dict[str, Any]:
    coordinates = raw.get("gps_coordinates")
    if not isinstance(coordinates, dict):
        coordinates = None
    return {
        "name": raw.get("title"),
        "category": raw.get("type"),
        "address": raw.get("address"),
        "rating": raw.get("rating"),
        "review_count": raw.get("reviews"),
        "phone": raw.get("phone"),
        "website": raw.get("website"),
        "coordinates": coordinates,
        "open_state": raw.get("open_state"),
        "image": raw.get("thumbnail"),
        "place_id": raw.get("place_id"),
        "data_id": raw.get("data_id"),
    }


async def resolve_locations(
    query: str = "",
    *,
    count: int = 5,
    client: LocationClient | None = None,
) -> list[dict[str, Any]]:
    """Resolve a city or place name to normalized coordinates."""
    normalized_count = _integer("count", count, 1, 10)
    normalized_query = _text("query", query)
    provider = client or LocationClient()
    payload = await provider.get_json(
        provider.geocoding_url,
        {
            "name": normalized_query,
            "count": normalized_count,
            "language": "en",
            "format": "json",
        },
        provider="Geocoding provider",
    )
    results = payload.get("results")
    if not isinstance(results, list):
        return []
    return [
        _normalize_location(result)
        for result in results[:normalized_count]
        if isinstance(result, dict)
    ]


async def search_places(
    query: str,
    *,
    near: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    zoom: int = 13,
    client: LocationClient | None = None,
) -> list[dict[str, Any]]:
    """Search local places with optional place-name or coordinate biasing."""
    normalized_query = _text("query", query)
    normalized_zoom = _integer("zoom", zoom, 1, 21)
    if (latitude is None) != (longitude is None):
        raise InvalidInputError("latitude and longitude must be provided together")

    normalized_latitude: float | None = None
    normalized_longitude: float | None = None
    if latitude is not None and longitude is not None:
        normalized_latitude = _coordinate("latitude", latitude, -90, 90)
        normalized_longitude = _coordinate("longitude", longitude, -180, 180)

    provider = client or LocationClient()
    normalized_near = _text("near", near) if near is not None else None
    if normalized_latitude is None and normalized_near is not None:
        locations = await resolve_locations(normalized_near, count=1, client=provider)
        if not locations:
            raise LocationNotFoundError(f"Location not found: {normalized_near}")
        normalized_latitude = _coordinate(
            "latitude", locations[0].get("latitude"), -90, 90
        )
        normalized_longitude = _coordinate(
            "longitude", locations[0].get("longitude"), -180, 180
        )

    if not provider.api_key:
        raise LocationProviderError("SERPAPI_API_KEY is not configured")

    params: dict[str, Any] = {
        "engine": "google_maps",
        "q": (
            f"{normalized_query} near {normalized_near}"
            if normalized_near
            else normalized_query
        ),
        "type": "search",
        "hl": "en",
    }
    if normalized_latitude is not None and normalized_longitude is not None:
        params["ll"] = (
            f"@{normalized_latitude:g},{normalized_longitude:g},{normalized_zoom}z"
        )
    params["api_key"] = provider.api_key

    payload = await provider.get_json(
        provider.serpapi_url, params, provider="Place-search provider"
    )
    results = payload.get("local_results")
    if not isinstance(results, list):
        return []
    return [
        _normalize_place(result) for result in results[:10] if isinstance(result, dict)
    ]
