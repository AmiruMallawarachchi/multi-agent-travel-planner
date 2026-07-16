"""Async Frankfurter reference-rate adapter."""

from __future__ import annotations

import os
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://api.frankfurter.dev/v1"
DEFAULT_FALLBACK_BASE_URL = "https://open.er-api.com/v6/latest"
REQUEST_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=10.0, pool=5.0)


class CurrencyProviderError(RuntimeError):
    """Frankfurter transport or response failure."""


class InvalidInputError(ValueError):
    """Currency input failed validation before a provider request."""


class FrankfurterClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (
            (base_url or os.getenv("FRANKFURTER_BASE_URL") or DEFAULT_BASE_URL)
            .strip()
            .rstrip("/")
        )
        self.transport = transport

    async def get_json(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT, transport=self.transport
            ) as client:
                response = await client.get(
                    f"{self.base_url}/{path.lstrip('/')}", params=params
                )
        except httpx.TimeoutException:
            raise CurrencyProviderError("Currency provider request timed out") from None
        except httpx.RequestError:
            raise CurrencyProviderError("Currency provider request failed") from None

        if response.status_code >= 400:
            raise CurrencyProviderError(
                f"Currency provider returned HTTP {response.status_code}"
            )
        try:
            payload = response.json()
        except ValueError:
            raise CurrencyProviderError(
                "Currency provider returned invalid JSON"
            ) from None
        if not isinstance(payload, dict):
            raise CurrencyProviderError(
                "Currency provider returned an unexpected response"
            )
        return payload


class OpenExchangeClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("OPEN_EXCHANGE_BASE_URL")
            or DEFAULT_FALLBACK_BASE_URL
        ).strip().rstrip("/")
        self.transport = transport

    async def latest(self, base: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT, transport=self.transport
            ) as client:
                response = await client.get(f"{self.base_url}/{base}")
        except httpx.TimeoutException:
            raise CurrencyProviderError("Fallback currency request timed out") from None
        except httpx.RequestError:
            raise CurrencyProviderError("Fallback currency request failed") from None

        if response.status_code >= 400:
            raise CurrencyProviderError(
                f"Fallback currency provider returned HTTP {response.status_code}"
            )
        try:
            payload = response.json()
        except ValueError:
            raise CurrencyProviderError(
                "Fallback currency provider returned invalid JSON"
            ) from None
        if not isinstance(payload, dict) or payload.get("result") != "success":
            raise CurrencyProviderError(
                "Fallback currency provider returned an unexpected response"
            )
        return payload


def _currency(value: Any) -> str:
    normalized = str(value or "").strip().upper()
    if len(normalized) != 3 or not normalized.isalpha():
        raise InvalidInputError("currency must be a 3-letter currency code")
    return normalized


def _amount(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise InvalidInputError("amount must be a number")
    try:
        normalized = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise InvalidInputError("amount must be a number") from None
    if not normalized.is_finite():
        raise InvalidInputError("amount must be a number")
    if normalized <= 0:
        raise InvalidInputError("amount must be greater than zero")
    return normalized


def _historical_date(value: str | None) -> date | None:
    if value is None:
        return None
    try:
        normalized = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise InvalidInputError(
            "date_value must be a valid calendar date in YYYY-MM-DD format"
        ) from None
    if normalized > date.today():
        raise InvalidInputError("date_value cannot be in the future")
    return normalized


def _number(value: Any, label: str) -> Decimal:
    if isinstance(value, bool):
        raise CurrencyProviderError(f"Currency provider returned an invalid {label}")
    try:
        normalized = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise CurrencyProviderError(
            f"Currency provider returned an invalid {label}"
        ) from None
    if not normalized.is_finite() or normalized <= 0:
        raise CurrencyProviderError(f"Currency provider returned an invalid {label}")
    return normalized


def _should_try_fallback(exc: CurrencyProviderError) -> bool:
    return "HTTP 404" in str(exc)


async def _fallback_exchange_rate(
    base_currency: str,
    quote_currency: str,
    *,
    client: OpenExchangeClient | None = None,
) -> dict[str, Any]:
    provider = client or OpenExchangeClient()
    payload = await provider.latest(base_currency)
    rates = payload.get("rates")
    if not isinstance(rates, dict) or quote_currency not in rates:
        raise CurrencyProviderError(
            f"Currency provider did not return a {base_currency}/{quote_currency} rate"
        )
    rate = _number(rates[quote_currency], "exchange rate")
    as_of = str(payload.get("time_last_update_utc") or date.today().isoformat())
    return {
        "from_currency": base_currency,
        "to_currency": quote_currency,
        "rate": float(rate),
        "as_of": as_of,
        "source": "ExchangeRate-API open reference rates",
    }


async def get_exchange_rate(
    base: str,
    quote: str,
    *,
    date_value: str | None = None,
    client: FrankfurterClient | None = None,
    fallback_client: OpenExchangeClient | None = None,
) -> dict[str, Any]:
    """Return a current or historical reference exchange rate."""
    base_currency = _currency(base)
    quote_currency = _currency(quote)
    requested_date = _historical_date(date_value)

    if base_currency == quote_currency:
        return {
            "from_currency": base_currency,
            "to_currency": quote_currency,
            "rate": 1.0,
            "as_of": (
                requested_date.isoformat()
                if requested_date is not None
                else date.today().isoformat()
            ),
            "source": "Frankfurter reference rates",
        }

    provider = client or FrankfurterClient()
    path = requested_date.isoformat() if requested_date is not None else "latest"
    try:
        payload = await provider.get_json(
            path, {"base": base_currency, "symbols": quote_currency}
        )
    except CurrencyProviderError as exc:
        if requested_date is None and _should_try_fallback(exc):
            return await _fallback_exchange_rate(
                base_currency, quote_currency, client=fallback_client
            )
        raise
    rates = payload.get("rates")
    if not isinstance(rates, dict) or quote_currency not in rates:
        exc = CurrencyProviderError(
            f"Currency provider did not return a {base_currency}/{quote_currency} rate"
        )
        if requested_date is None and _should_try_fallback(exc):
            return await _fallback_exchange_rate(
                base_currency, quote_currency, client=fallback_client
            )
        raise exc
    rate = _number(rates[quote_currency], "exchange rate")
    as_of = str(payload.get("date") or path)
    return {
        "from_currency": base_currency,
        "to_currency": quote_currency,
        "rate": float(rate),
        "as_of": as_of,
        "source": "Frankfurter reference rates",
    }


async def convert_currency(
    amount: Any,
    from_currency: str,
    to_currency: str,
    *,
    date_value: str | None = None,
    client: FrankfurterClient | None = None,
    fallback_client: OpenExchangeClient | None = None,
) -> dict[str, Any]:
    """Convert an amount using a current or historical reference rate."""
    normalized_amount = _amount(amount)
    result = await get_exchange_rate(
        from_currency,
        to_currency,
        date_value=date_value,
        client=client,
        fallback_client=fallback_client,
    )
    rate = Decimal(str(result["rate"]))
    converted = (normalized_amount * rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return {
        "amount": float(normalized_amount),
        "from_currency": result["from_currency"],
        "to_currency": result["to_currency"],
        "rate": result["rate"],
        "converted_amount": float(converted),
        "as_of": result["as_of"],
        "source": result["source"],
    }


async def list_supported_currencies(
    *, client: FrankfurterClient | None = None
) -> list[dict[str, str]]:
    """List currencies exposed by the provider in stable code order."""
    provider = client or FrankfurterClient()
    payload = await provider.get_json("currencies")
    currencies = []
    for code, name in payload.items():
        normalized_code = str(code).strip().upper()
        normalized_name = str(name).strip()
        if len(normalized_code) == 3 and normalized_code.isalpha() and normalized_name:
            currencies.append({"code": normalized_code, "name": normalized_name})
    if not currencies:
        raise CurrencyProviderError("Currency provider did not return any currencies")
    return sorted(currencies, key=lambda currency: currency["code"])
