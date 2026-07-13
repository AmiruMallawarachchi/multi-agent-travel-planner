from __future__ import annotations

import httpx
import pytest

from mcp_servers.currency_mcp import frankfurter_client as currency_client


BASE_URL = "https://currency.test/v1"


def make_client(handler) -> currency_client.FrankfurterClient:
    transport = (
        handler
        if isinstance(handler, httpx.MockTransport)
        else httpx.MockTransport(handler)
    )
    return currency_client.FrankfurterClient(
        base_url=BASE_URL,
        transport=transport,
    )


@pytest.mark.asyncio
async def test_maps_latest_rate_and_converts_amount():
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured.update(dict(request.url.params))
        return httpx.Response(
            200,
            json={
                "amount": 1.0,
                "base": "USD",
                "date": "2026-07-10",
                "rates": {"EUR": 0.86},
            },
        )

    result = await currency_client.convert_currency(
        amount=125.5,
        from_currency="usd",
        to_currency="eur",
        client=make_client(handler),
    )

    assert captured == {"path": "/v1/latest", "base": "USD", "symbols": "EUR"}
    assert result == {
        "amount": 125.5,
        "from_currency": "USD",
        "to_currency": "EUR",
        "rate": 0.86,
        "converted_amount": 107.93,
        "as_of": "2026-07-10",
        "source": "Frankfurter reference rates",
    }


@pytest.mark.asyncio
async def test_historical_rate_uses_date_path():
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(
            200,
            json={"base": "GBP", "date": "2025-01-15", "rates": {"JPY": 190.25}},
        )

    result = await currency_client.get_exchange_rate(
        "GBP", "JPY", date_value="2025-01-15", client=make_client(handler)
    )

    assert captured["path"] == "/v1/2025-01-15"
    assert result["rate"] == 190.25
    assert result["as_of"] == "2025-01-15"


@pytest.mark.asyncio
async def test_same_currency_skips_network():
    def fail_if_called(_request: httpx.Request) -> httpx.Response:
        pytest.fail("same-currency conversion should not call the provider")

    result = await currency_client.convert_currency(
        20, "LKR", "lkr", client=make_client(fail_if_called)
    )

    assert result["rate"] == 1.0
    assert result["converted_amount"] == 20.0


@pytest.mark.asyncio
async def test_lists_supported_currencies_in_stable_order():
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200, json={"USD": "United States Dollar", "EUR": "Euro"}
        )
    )

    result = await currency_client.list_supported_currencies(
        client=make_client(transport)
    )

    assert result == [
        {"code": "EUR", "name": "Euro"},
        {"code": "USD", "name": "United States Dollar"},
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"amount": 0}, "amount must be greater"),
        ({"amount": True}, "amount must be a number"),
        ({"from_currency": "US"}, "3-letter currency"),
        ({"to_currency": "EURO"}, "3-letter currency"),
        ({"date_value": "2025-02-30"}, "valid calendar date"),
        ({"date_value": "2099-01-01"}, "future"),
    ],
)
async def test_rejects_invalid_inputs_before_network(overrides: dict, message: str):
    def fail_if_called(_request: httpx.Request) -> httpx.Response:
        pytest.fail("network should not be called")

    arguments = {
        "amount": 10,
        "from_currency": "USD",
        "to_currency": "EUR",
        "date_value": None,
        "client": make_client(fail_if_called),
    }
    arguments.update(overrides)

    with pytest.raises(currency_client.InvalidInputError, match=message):
        await currency_client.convert_currency(**arguments)


@pytest.mark.asyncio
async def test_missing_rate_is_a_controlled_provider_error():
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200, json={"base": "USD", "date": "2026-07-10", "rates": {}}
        )
    )

    with pytest.raises(currency_client.CurrencyProviderError, match="did not return"):
        await currency_client.get_exchange_rate(
            "USD", "EUR", client=make_client(transport)
        )


@pytest.mark.asyncio
async def test_http_error_does_not_echo_response_body():
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(500, text="internal provider details")
    )

    with pytest.raises(currency_client.CurrencyProviderError) as exc_info:
        await currency_client.convert_currency(
            10, "USD", "EUR", client=make_client(transport)
        )

    assert str(exc_info.value) == "Currency provider returned HTTP 500"
    assert "internal provider details" not in str(exc_info.value)
