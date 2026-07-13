"""Async SerpApi adapter for normalized Google Hotels search results."""

from __future__ import annotations

import os
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

DEFAULT_SERPAPI_BASE_URL = "https://serpapi.com/search.json"
MAX_RESULTS = 10
REQUEST_TIMEOUT = httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0)

_CURRENCY_RE = re.compile(r"^[A-Za-z]{3}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HOTEL_QUERY_TERMS = ("hotel", "hotels", "resort", "resorts", "hostel", "hostels")
_RATING_FILTERS = {7, 8, 9}


class SerpApiError(RuntimeError):
    """SerpApi configuration, transport, or response failure."""


class InvalidInputError(ValueError):
    """Input failed validation before a provider request was made."""


class SerpApiClient:
    """Owns HTTP concerns so search normalization remains deterministic."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = (
            os.getenv("SERPAPI_API_KEY", "") if api_key is None else api_key
        ).strip()
        configured_url = (
            os.getenv("SERPAPI_BASE_URL", DEFAULT_SERPAPI_BASE_URL)
            if base_url is None
            else base_url
        )
        self._base_url = configured_url.strip() or DEFAULT_SERPAPI_BASE_URL
        self._transport = transport

    async def search(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self._api_key:
            raise SerpApiError("SERPAPI_API_KEY is not configured")

        query = {**params, "api_key": self._api_key}
        try:
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT, transport=self._transport
            ) as client:
                response = await client.get(self._base_url, params=query)
        except httpx.TimeoutException:
            raise SerpApiError("SerpApi request timed out") from None
        except httpx.RequestError:
            # Request exceptions can contain the full URL, including api_key.
            raise SerpApiError("SerpApi request failed") from None

        try:
            payload = response.json()
        except ValueError:
            raise SerpApiError("SerpApi returned an invalid JSON response") from None

        if not isinstance(payload, dict):
            raise SerpApiError("SerpApi returned an unexpected response")

        provider_error = _redact_provider_message(payload.get("error"), self._api_key)
        if response.status_code >= 400:
            detail = f": {provider_error}" if provider_error else ""
            raise SerpApiError(f"SerpApi returned HTTP {response.status_code}{detail}")
        if provider_error:
            raise SerpApiError(f"SerpApi search failed: {provider_error}")

        metadata = payload.get("search_metadata")
        if isinstance(metadata, dict) and metadata.get("status") == "Error":
            raise SerpApiError("SerpApi search failed")
        return payload


def _redact_provider_message(value: Any, api_key: str) -> str:
    if not isinstance(value, str):
        return ""
    message = value.replace(api_key, "[redacted]") if api_key else value
    return message[:300]


def _validate_query(destination: str) -> str:
    normalized = " ".join((destination or "").split())
    if not normalized:
        raise InvalidInputError("destination or hotel query is required")
    if len(normalized) > 200:
        raise InvalidInputError(
            "destination or hotel query must be 200 characters or fewer"
        )
    words = {word.strip(".,").casefold() for word in normalized.split()}
    if words.intersection(_HOTEL_QUERY_TERMS):
        return normalized
    return f"Hotels in {normalized}"


def _validate_date(label: str, value: str) -> date:
    if not _DATE_RE.fullmatch(value or ""):
        raise InvalidInputError(f"{label} must be in YYYY-MM-DD format")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise InvalidInputError(f"{label} must be a valid calendar date") from None


def _validate_integer(label: str, value: int, minimum: int, maximum: int) -> int:
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


def _validate_currency(value: str) -> str:
    normalized = (value or "").strip().upper()
    if not _CURRENCY_RE.fullmatch(normalized):
        raise InvalidInputError("currency must be a 3-letter currency code, e.g. 'USD'")
    return normalized


def _validate_optional_price(label: str, value: int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise InvalidInputError(f"{label} must be greater than zero")
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        raise InvalidInputError(f"{label} must be greater than zero") from None
    if isinstance(value, float) and not value.is_integer():
        raise InvalidInputError(f"{label} must be greater than zero")
    if normalized <= 0:
        raise InvalidInputError(f"{label} must be greater than zero")
    return normalized


def _first_image(raw: dict[str, Any]) -> str | None:
    images = raw.get("images")
    if isinstance(images, list):
        for image in images:
            if isinstance(image, dict):
                url = image.get("original_image") or image.get("thumbnail")
                if isinstance(url, str) and url:
                    return url
    thumbnail = raw.get("thumbnail")
    return thumbnail if isinstance(thumbnail, str) and thumbnail else None


def _coordinates(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    latitude = raw.get("latitude")
    longitude = raw.get("longitude")
    if latitude is None or longitude is None:
        return None
    return {"latitude": latitude, "longitude": longitude}


def _normalize_property(raw: Any, currency: str) -> dict[str, Any] | None:
    if not isinstance(raw, dict) or not raw.get("name"):
        return None
    rate = raw.get("rate_per_night")
    price_per_night = rate.get("extracted_lowest") if isinstance(rate, dict) else None
    if price_per_night is None:
        price_per_night = raw.get("extracted_price")
    amenities = raw.get("amenities")
    return {
        "name": raw.get("name"),
        "description": raw.get("description"),
        "price_per_night": price_per_night,
        "currency": currency,
        "overall_rating": raw.get("overall_rating"),
        "review_count": raw.get("reviews"),
        "hotel_class": raw.get("hotel_class") or raw.get("extracted_hotel_class"),
        "amenities": amenities if isinstance(amenities, list) else [],
        "image": _first_image(raw),
        "coordinates": _coordinates(raw.get("gps_coordinates")),
        "property_token": raw.get("property_token"),
    }


async def search_hotel_properties(
    destination: str,
    check_in_date: str,
    check_out_date: str,
    adults: int = 2,
    children: int = 0,
    currency: str = "USD",
    min_price: int | None = None,
    max_price: int | None = None,
    rating: int | None = None,
    limit: int = MAX_RESULTS,
    *,
    client: SerpApiClient | None = None,
) -> list[dict[str, Any]]:
    """Search and normalize Google Hotels properties for a destination/query."""
    query = _validate_query(destination)
    check_in = _validate_date("check_in_date", check_in_date)
    check_out = _validate_date("check_out_date", check_out_date)
    if check_out <= check_in:
        raise InvalidInputError("check_out_date must be after check_in_date")

    adults = _validate_integer("adults", adults, 1, 10)
    children = _validate_integer("children", children, 0, 10)
    if adults + children > 10:
        raise InvalidInputError("total guests must not exceed 10")
    currency = _validate_currency(currency)
    min_price = _validate_optional_price("min_price", min_price)
    max_price = _validate_optional_price("max_price", max_price)
    if min_price is not None and max_price is not None and max_price < min_price:
        raise InvalidInputError("max_price must be greater than or equal to min_price")
    if rating is not None and rating not in _RATING_FILTERS:
        raise InvalidInputError("rating must be one of 7 (3.5+), 8 (4.0+), or 9 (4.5+)")
    limit = _validate_integer("limit", limit, 1, MAX_RESULTS)

    params: dict[str, Any] = {
        "engine": "google_hotels",
        "q": query,
        "check_in_date": check_in.isoformat(),
        "check_out_date": check_out.isoformat(),
        "adults": adults,
        "children": children,
        "currency": currency,
    }
    if min_price is not None:
        params["min_price"] = min_price
    if max_price is not None:
        params["max_price"] = max_price
    if rating is not None:
        params["rating"] = rating

    payload = await (client or SerpApiClient()).search(params)
    raw_properties = payload.get("properties")
    if not isinstance(raw_properties, list):
        return []

    normalized: list[dict[str, Any]] = []
    for raw_property in raw_properties:
        property_result = _normalize_property(raw_property, currency)
        if property_result is not None:
            normalized.append(property_result)
        if len(normalized) == limit:
            break
    return normalized


async def list_hotels(
    destination: str, limit: int = MAX_RESULTS
) -> list[dict[str, Any]]:
    """Compatibility overview using a one-night stay beginning tomorrow."""
    check_in = date.today() + timedelta(days=1)
    check_out = check_in + timedelta(days=1)
    return await search_hotel_properties(
        destination,
        check_in.isoformat(),
        check_out.isoformat(),
        limit=limit,
    )


async def book_hotel_offer(offer_id: str, guest_name: str) -> dict[str, Any]:
    """Return a clearly labelled simulated booking confirmation."""
    if not offer_id or len(offer_id) > 200:
        raise InvalidInputError("offer_id is missing or unreasonably long")
    guest_name = (guest_name or "").strip()[:200]
    if not guest_name:
        raise InvalidInputError("guest_name is required")

    return {
        "confirmation_number": f"TW-H-{uuid.uuid4().hex[:8].upper()}",
        "offer_id": offer_id,
        "guest_name": guest_name,
        "status": "confirmed",
        "booked_at": datetime.now(timezone.utc).isoformat(),
        "simulated": True,
    }
