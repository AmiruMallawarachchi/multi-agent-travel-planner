"""
mcp_servers/flight_mcp/amadeus_client.py
Thin, resilient wrapper around the Amadeus for Developers self-service TEST
API. This is the ONLY file that knows Amadeus's request/response shape -
server.py speaks in plain dicts, so swapping providers later means editing
this file only (SRS 9-E1).

Booking note: Amadeus's real Flight Create Orders endpoint needs full
traveler documents and payment details, out of scope here. book_flight_offer
returns a realistically-shaped SIMULATED confirmation instead - clearly
labelled `"simulated": True` - matching the interface a real booking
provider would need, so plugging one in later doesn't touch server.py or
any agent code.
"""
from __future__ import annotations

import os
import re
import time
import uuid
from datetime import datetime, timezone

import httpx

AMADEUS_BASE_URL = os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com")
AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID", "")
AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET", "")
REQUEST_TIMEOUT_SECONDS = 15.0

_AIRPORT_CODE_RE = re.compile(r"^[A-Za-z]{3}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_token_cache: dict[str, float | str] = {"token": "", "expires_at": 0.0}


class AmadeusError(RuntimeError):
    """Raised for any Amadeus failure - config, auth, network, or a bad
    response. server.py always catches this and returns a graceful
    `{"ok": False, ...}` tool result (SRS section 5)."""


class InvalidInputError(ValueError):
    """Input failed validation before any network call was made - defence
    in depth, the MCP server never trusts its caller's arguments blindly."""


def _validate_airport_code(label: str, code: str) -> str:
    if not _AIRPORT_CODE_RE.match(code or ""):
        raise InvalidInputError(f"{label} must be a 3-letter IATA airport code, e.g. 'LHR'")
    return code.upper()


def _validate_date(label: str, value: str) -> str:
    if not _DATE_RE.match(value or ""):
        raise InvalidInputError(f"{label} must be in YYYY-MM-DD format")
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


async def list_flights(origin: str, destination: str, limit: int = 10) -> list[dict]:
    """Real Amadeus call: cheapest-dates style overview isn't in scope for
    the test tier, so 'list' reuses a same-day, single-adult search as a
    lightweight overview of what's flying this route."""
    origin = _validate_airport_code("origin", origin)
    destination = _validate_airport_code("destination", destination)
    today = datetime.now(timezone.utc).date().isoformat()
    return await search_flight_offers(origin, destination, today, adults=1, limit=limit)


async def search_flight_offers(
    origin: str, destination: str, departure_date: str, adults: int = 1, limit: int = 5
) -> list[dict]:
    """Real Amadeus call: priced, available flight offers for a route/date."""
    origin = _validate_airport_code("origin", origin)
    destination = _validate_airport_code("destination", destination)
    departure_date = _validate_date("departure_date", departure_date)
    adults = max(1, min(int(adults), 9))
    limit = max(1, min(int(limit), 20))

    data = await _get(
        "/v2/shopping/flight-offers",
        {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": adults,
            "max": limit,
            "currencyCode": "USD",
        },
    )
    return data.get("data", [])[:limit]


async def book_flight_offer(offer_id: str, traveller_name: str) -> dict:
    """SIMULATED booking - see module docstring for why."""
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
