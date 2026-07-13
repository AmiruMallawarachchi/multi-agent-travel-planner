"""Async SerpApi adapter for normalized Google Flights search results."""

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

_AIRPORT_CODE_RE = re.compile(r"^[A-Za-z]{3}$")
_CURRENCY_RE = re.compile(r"^[A-Za-z]{3}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TRAVEL_CLASSES = {1: "Economy", 2: "Premium economy", 3: "Business", 4: "First"}


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


def _validate_airport_code(label: str, value: str) -> str:
    normalized = (value or "").strip().upper()
    if not _AIRPORT_CODE_RE.fullmatch(normalized):
        raise InvalidInputError(
            f"{label} must be a 3-letter IATA airport code, e.g. 'LHR'"
        )
    return normalized


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


def _validate_travel_class(value: int) -> int:
    try:
        normalized = _validate_integer("travel_class", value, 1, 4)
    except InvalidInputError:
        raise InvalidInputError(
            "travel_class must be one of 1 (economy), 2 (premium economy), 3 (business), or 4 (first)"
        ) from None
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


def _normalize_airport(raw: Any) -> dict[str, Any]:
    airport = raw if isinstance(raw, dict) else {}
    return {
        "airport_code": airport.get("id"),
        "airport_name": airport.get("name"),
        "time": airport.get("time"),
    }


def _normalize_segment(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "airline": raw.get("airline"),
        "flight_number": raw.get("flight_number"),
        "departure": _normalize_airport(raw.get("departure_airport")),
        "arrival": _normalize_airport(raw.get("arrival_airport")),
        "duration_minutes": raw.get("duration"),
        "travel_class": raw.get("travel_class"),
        "airplane": raw.get("airplane"),
    }


def _normalize_layover(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "airport_code": raw.get("id"),
        "airport_name": raw.get("name"),
        "duration_minutes": raw.get("duration"),
    }


def _normalize_option(
    raw: Any, currency: str, travel_class: int
) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    raw_segments = raw.get("flights")
    if not isinstance(raw_segments, list):
        return None
    segments = [
        _normalize_segment(segment)
        for segment in raw_segments
        if isinstance(segment, dict)
    ]
    if not segments:
        return None

    raw_layovers = raw.get("layovers")
    layovers = (
        [
            _normalize_layover(layover)
            for layover in raw_layovers
            if isinstance(layover, dict)
        ]
        if isinstance(raw_layovers, list)
        else []
    )
    first_segment = segments[0]
    last_segment = segments[-1]
    return {
        "airline": first_segment["airline"],
        "flight_number": first_segment["flight_number"],
        "departure": first_segment["departure"],
        "arrival": last_segment["arrival"],
        "segments": segments,
        "layovers": layovers,
        "total_duration_minutes": raw.get("total_duration"),
        "price": raw.get("price"),
        "currency": currency,
        "travel_class": first_segment["travel_class"] or _TRAVEL_CLASSES[travel_class],
        "booking_token": raw.get("booking_token"),
    }


async def search_flight_offers(
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    return_date: str | None = None,
    adults: int = 1,
    children: int = 0,
    travel_class: int = 1,
    currency: str = "USD",
    max_price: int | None = None,
    limit: int = MAX_RESULTS,
    *,
    client: SerpApiClient | None = None,
) -> list[dict[str, Any]]:
    """Search and normalize one-way or round-trip Google Flights results."""
    departure_id = _validate_airport_code("departure_id", departure_id)
    arrival_id = _validate_airport_code("arrival_id", arrival_id)
    if departure_id == arrival_id:
        raise InvalidInputError("departure_id and arrival_id must be different")

    outbound = _validate_date("outbound_date", outbound_date)
    inbound = _validate_date("return_date", return_date) if return_date else None
    if inbound and inbound <= outbound:
        raise InvalidInputError("return_date must be after outbound_date")

    adults = _validate_integer("adults", adults, 1, 9)
    children = _validate_integer("children", children, 0, 9)
    if adults + children > 9:
        raise InvalidInputError("total passengers must not exceed 9")
    travel_class = _validate_travel_class(travel_class)
    currency = _validate_currency(currency)
    max_price = _validate_optional_price("max_price", max_price)
    limit = _validate_integer("limit", limit, 1, MAX_RESULTS)

    params: dict[str, Any] = {
        "engine": "google_flights",
        "departure_id": departure_id,
        "arrival_id": arrival_id,
        "outbound_date": outbound.isoformat(),
        "type": 1 if inbound else 2,
        "adults": adults,
        "children": children,
        "travel_class": travel_class,
        "currency": currency,
    }
    if inbound:
        params["return_date"] = inbound.isoformat()
    if max_price is not None:
        params["max_price"] = max_price

    payload = await (client or SerpApiClient()).search(params)
    best = (
        payload.get("best_flights")
        if isinstance(payload.get("best_flights"), list)
        else []
    )
    other = (
        payload.get("other_flights")
        if isinstance(payload.get("other_flights"), list)
        else []
    )

    normalized: list[dict[str, Any]] = []
    for raw_option in [*best, *other]:
        option = _normalize_option(raw_option, currency, travel_class)
        if option is not None:
            normalized.append(option)
        if len(normalized) == limit:
            break
    return normalized


async def list_flights(
    departure_id: str, arrival_id: str, limit: int = MAX_RESULTS
) -> list[dict[str, Any]]:
    """Compatibility overview using a one-way search for tomorrow."""
    outbound_date = (date.today() + timedelta(days=1)).isoformat()
    return await search_flight_offers(
        departure_id, arrival_id, outbound_date, limit=limit
    )


async def book_flight_offer(offer_id: str, traveller_name: str) -> dict[str, Any]:
    """Return a clearly labelled simulated booking confirmation."""
    if not offer_id or len(offer_id) > 200:
        raise InvalidInputError("offer_id is missing or unreasonably long")
    traveller_name = (traveller_name or "").strip()[:200]
    if not traveller_name:
        raise InvalidInputError("traveller_name is required")

    return {
        "confirmation_number": f"TW-F-{uuid.uuid4().hex[:8].upper()}",
        "offer_id": offer_id,
        "traveller_name": traveller_name,
        "status": "confirmed",
        "booked_at": datetime.now(timezone.utc).isoformat(),
        "simulated": True,
    }
