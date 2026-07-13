"""
mcp_servers/hotel_mcp/amadeus_client.py
Thin, resilient wrapper around the Amadeus for Developers self-service TEST
API. This is the ONLY file that knows Amadeus's request/response shape -
server.py speaks in plain dicts, so swapping providers later means editing
this file, not the MCP tool definitions or any agent code (SRS 9-E1).

Booking note: real Amadeus hotel booking needs PCI-scope payment details,
which is out of scope for this project. book_hotel_offer below returns a
realistically-shaped SIMULATED confirmation instead - clearly labelled
`"simulated": True` - so the interface a real booking provider would need
to match is already correct, and nothing calling this function needs to
change when you plug one in.
"""
from __future__ import annotations

import os
import re
import time
import uuid
from datetime import date, datetime, timezone

import httpx

AMADEUS_BASE_URL = os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com")
AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID", "")
AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET", "")
REQUEST_TIMEOUT_SECONDS = 15.0

_CITY_CODE_RE = re.compile(r"^[A-Za-z]{3}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_token_cache: dict[str, float | str] = {"token": "", "expires_at": 0.0}


class AmadeusError(RuntimeError):
    """Raised for any Amadeus failure - config, auth, network, or a bad
    response. Callers (server.py) always catch this and turn it into a
    graceful `{"ok": False, ...}` tool result - see SRS section 5."""


class InvalidInputError(ValueError):
    """Raised when the caller's arguments fail validation, before any
    network call is made. Defence in depth: the MCP server validates its
    own inputs and never trusts whatever called it, agent or otherwise."""


def _validate_city_code(city_code: str) -> str:
    if not _CITY_CODE_RE.match(city_code or ""):
        raise InvalidInputError("city_code must be a 3-letter IATA city code, e.g. 'PAR'")
    return city_code.upper()


def _validate_date(label: str, value: str) -> date:
    if not _DATE_RE.match(value or ""):
        raise InvalidInputError(f"{label} must be in YYYY-MM-DD format")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise InvalidInputError(f"{label} must be a valid calendar date") from exc


def _validate_adults(adults: int) -> int:
    try:
        value = int(adults)
    except (TypeError, ValueError) as exc:
        raise InvalidInputError("adults must be an integer from 1 to 9") from exc
    if not 1 <= value <= 9:
        raise InvalidInputError("adults must be between 1 and 9")
    return value


async def _get_access_token(client: httpx.AsyncClient) -> str:
    if _token_cache["token"] and time.time() < float(_token_cache["expires_at"]) - 30:
        return str(_token_cache["token"])

    if not AMADEUS_CLIENT_ID or not AMADEUS_CLIENT_SECRET:
        raise AmadeusError("AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET are not configured")

    resp = await client.post(
        f"{AMADEUS_BASE_URL}/v1/security/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": AMADEUS_CLIENT_ID,
            "client_secret": AMADEUS_CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.status_code >= 400:
        # Deliberately don't include resp.text here - avoid ever echoing
        # anything that could contain credential-adjacent detail into logs.
        raise AmadeusError(f"Amadeus auth failed with status {resp.status_code}")
    payload = resp.json()
    _token_cache["token"] = payload["access_token"]
    _token_cache["expires_at"] = time.time() + payload["expires_in"]
    return str(_token_cache["token"])


async def _get(path: str, params: dict) -> dict:
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        token = await _get_access_token(client)
        resp = await client.get(
            f"{AMADEUS_BASE_URL}{path}",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code >= 400:
            raise AmadeusError(f"Amadeus {path} returned HTTP {resp.status_code}")
        return resp.json()


async def list_hotels_by_city(city_code: str, limit: int = 20) -> list[dict]:
    """Real Amadeus call: hotels available in a city (no pricing yet)."""
    city_code = _validate_city_code(city_code)
    data = await _get("/v1/reference-data/locations/hotels/by-city", {"cityCode": city_code})
    return data.get("data", [])[: max(1, min(limit, 50))]


async def search_hotel_offers(
    city_code: str, check_in: str, check_out: str, adults: int = 1, limit: int = 5
) -> list[dict]:
    """Real Amadeus call: priced, available offers for hotels in a city.
    Note: queries the first 20 hotel ids found in the city per call - a
    production system would paginate; acceptable for this project's scope."""
    city_code = _validate_city_code(city_code)
    check_in_date = _validate_date("check_in", check_in)
    check_out_date = _validate_date("check_out", check_out)
    if check_out_date <= check_in_date:
        raise InvalidInputError("check_out must be after check_in")
    adults = _validate_adults(adults)

    hotels = await list_hotels_by_city(city_code, limit=20)
    hotel_ids = ",".join(h["hotelId"] for h in hotels if "hotelId" in h)
    if not hotel_ids:
        return []

    data = await _get(
        "/v3/shopping/hotel-offers",
        {
            "hotelIds": hotel_ids,
            "checkInDate": check_in_date.isoformat(),
            "checkOutDate": check_out_date.isoformat(),
            "adults": adults,
        },
    )
    return data.get("data", [])[: max(1, min(limit, 20))]


async def book_hotel_offer(offer_id: str, guest_name: str) -> dict:
    """SIMULATED booking - see module docstring for why. offer_id and
    guest_name are still validated so this function is safe to call with
    untrusted input even though it doesn't hit the network."""
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
