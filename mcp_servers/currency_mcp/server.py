"""FastMCP currency service backed by Frankfurter reference rates."""

from __future__ import annotations

import os
from typing import Any, Awaitable, Callable

from dotenv import load_dotenv
from fastmcp import FastMCP
from frankfurter_client import (
    CurrencyProviderError,
    InvalidInputError,
    convert_currency as convert_reference_currency,
    get_exchange_rate as fetch_exchange_rate,
    list_supported_currencies as fetch_supported_currencies,
)
from starlette.requests import Request
from starlette.responses import JSONResponse

load_dotenv()

mcp = FastMCP("currency-mcp")


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "currency-mcp"})


async def _currency_result(
    operation: Callable[..., Awaitable[Any]], **arguments: Any
) -> dict[str, Any]:
    try:
        return {"ok": True, "result": await operation(**arguments)}
    except InvalidInputError as exc:
        return {"ok": False, "error": str(exc)}
    except CurrencyProviderError as exc:
        return {"ok": False, "error": f"Currency service unavailable: {exc}"}


@mcp.tool()
async def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
    date_value: str | None = None,
) -> dict[str, Any]:
    """Convert an amount using current or historical reference rates."""
    return await _currency_result(
        convert_reference_currency,
        amount=amount,
        from_currency=from_currency,
        to_currency=to_currency,
        date_value=date_value,
    )


@mcp.tool()
async def get_exchange_rate(
    base: str, quote: str, date_value: str | None = None
) -> dict[str, Any]:
    """Get a current or historical reference exchange rate."""
    return await _currency_result(
        fetch_exchange_rate,
        base=base,
        quote=quote,
        date_value=date_value,
    )


@mcp.tool()
async def list_supported_currencies() -> dict[str, Any]:
    """List currencies supported by the reference-rate provider."""
    return await _currency_result(fetch_supported_currencies)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8005"))
    mcp.run(transport="http", host="0.0.0.0", port=port)
