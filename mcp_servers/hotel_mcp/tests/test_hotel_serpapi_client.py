from __future__ import annotations

import httpx
import pytest

from mcp_servers.hotel_mcp import serpapi_client as hotel_client


API_KEY = "test-serpapi-key"
BASE_URL = "https://serpapi.test/search.json"


def make_client(handler: httpx.MockTransport) -> hotel_client.SerpApiClient:
    return hotel_client.SerpApiClient(
        api_key=API_KEY,
        base_url=BASE_URL,
        transport=handler,
    )


def property_result(index: int = 1) -> dict:
    return {
        "name": f"Dubai Harbour Hotel {index}",
        "description": "Waterfront hotel near the marina.",
        "rate_per_night": {"lowest": "$185", "extracted_lowest": 185},
        "overall_rating": 4.7,
        "reviews": 824,
        "hotel_class": "5-star hotel",
        "amenities": ["Free Wi-Fi", "Pool"],
        "images": [
            {
                "thumbnail": "https://images.test/thumb.jpg",
                "original_image": "https://images.test/hotel.jpg",
            }
        ],
        "gps_coordinates": {"latitude": 25.081, "longitude": 55.141},
        "property_token": f"property-token-{index}",
    }


@pytest.mark.asyncio
async def test_maps_params_and_normalizes_properties():
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(dict(request.url.params))
        return httpx.Response(200, json={"properties": [property_result()]})

    results = await hotel_client.search_hotel_properties(
        destination="Dubai",
        check_in_date="2026-08-01",
        check_out_date="2026-08-07",
        adults=2,
        children=1,
        currency="usd",
        min_price=100,
        max_price=300,
        rating=8,
        client=make_client(httpx.MockTransport(handler)),
    )

    assert captured == {
        "engine": "google_hotels",
        "q": "Hotels in Dubai",
        "check_in_date": "2026-08-01",
        "check_out_date": "2026-08-07",
        "adults": "2",
        "children": "1",
        "currency": "USD",
        "min_price": "100",
        "max_price": "300",
        "rating": "8",
        "api_key": API_KEY,
    }
    assert results == [
        {
            "name": "Dubai Harbour Hotel 1",
            "description": "Waterfront hotel near the marina.",
            "price_per_night": 185,
            "currency": "USD",
            "overall_rating": 4.7,
            "review_count": 824,
            "hotel_class": "5-star hotel",
            "amenities": ["Free Wi-Fi", "Pool"],
            "image": "https://images.test/hotel.jpg",
            "coordinates": {"latitude": 25.081, "longitude": 55.141},
            "property_token": "property-token-1",
        }
    ]


@pytest.mark.asyncio
async def test_preserves_full_query_and_caps_results_at_ten():
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(dict(request.url.params))
        return httpx.Response(
            200, json={"properties": [property_result(index) for index in range(12)]}
        )

    results = await hotel_client.search_hotel_properties(
        "Hotels near Dubai Marina",
        "2026-08-01",
        "2026-08-07",
        client=make_client(httpx.MockTransport(handler)),
    )

    assert captured["q"] == "Hotels near Dubai Marina"
    assert len(results) == 10
    assert results[-1]["property_token"] == "property-token-9"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"destination": "  "}, "destination"),
        ({"check_in_date": "2026-02-30"}, "valid calendar date"),
        ({"check_out_date": "2026-07-31"}, "after check_in_date"),
        ({"adults": 0}, "adults must be between"),
        ({"children": -1}, "children must be between"),
        ({"currency": "US"}, "3-letter currency"),
        ({"min_price": 0}, "min_price must be greater"),
        ({"min_price": 400, "max_price": 300}, "max_price must be greater"),
        ({"rating": 5}, "rating must be one of"),
    ],
)
async def test_rejects_invalid_inputs_before_network(overrides: dict, message: str):
    def fail_if_called(_request: httpx.Request) -> httpx.Response:
        pytest.fail("network should not be called for invalid input")

    arguments = {
        "destination": "Dubai",
        "check_in_date": "2026-08-01",
        "check_out_date": "2026-08-07",
        "adults": 2,
        "children": 0,
        "currency": "USD",
        "min_price": None,
        "max_price": None,
        "rating": None,
        "client": make_client(httpx.MockTransport(fail_if_called)),
    }
    arguments.update(overrides)

    with pytest.raises(hotel_client.InvalidInputError, match=message):
        await hotel_client.search_hotel_properties(**arguments)


@pytest.mark.asyncio
async def test_missing_properties_return_an_empty_list():
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200, json={"search_metadata": {"status": "Success"}}
        )
    )

    results = await hotel_client.search_hotel_properties(
        "Dubai",
        "2026-08-01",
        "2026-08-07",
        client=make_client(transport),
    )

    assert results == []


@pytest.mark.asyncio
async def test_provider_errors_redact_the_api_key():
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            429, json={"error": f"Quota exceeded for {API_KEY}"}
        )
    )

    with pytest.raises(hotel_client.SerpApiError) as exc_info:
        await hotel_client.search_hotel_properties(
            "Dubai",
            "2026-08-01",
            "2026-08-07",
            client=make_client(transport),
        )

    assert API_KEY not in str(exc_info.value)
    assert "[redacted]" in str(exc_info.value)


@pytest.mark.asyncio
async def test_missing_api_key_fails_before_network():
    def fail_if_called(_request: httpx.Request) -> httpx.Response:
        pytest.fail("network should not be called without an API key")

    client = hotel_client.SerpApiClient(
        api_key="",
        base_url=BASE_URL,
        transport=httpx.MockTransport(fail_if_called),
    )

    with pytest.raises(
        hotel_client.SerpApiError, match="SERPAPI_API_KEY is not configured"
    ):
        await hotel_client.search_hotel_properties(
            "Dubai",
            "2026-08-01",
            "2026-08-07",
            client=client,
        )


@pytest.mark.asyncio
async def test_timeout_is_wrapped_without_leaking_the_request_url():
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(hotel_client.SerpApiError) as exc_info:
        await hotel_client.search_hotel_properties(
            "Dubai",
            "2026-08-01",
            "2026-08-07",
            client=make_client(httpx.MockTransport(timeout)),
        )

    assert str(exc_info.value) == "SerpApi request timed out"
    assert API_KEY not in str(exc_info.value)


@pytest.mark.asyncio
async def test_booking_remains_explicitly_simulated():
    confirmation = await hotel_client.book_hotel_offer("property-token", "Asha Perera")

    assert confirmation["confirmation_number"].startswith("TW-H-")
    assert confirmation["offer_id"] == "property-token"
    assert confirmation["guest_name"] == "Asha Perera"
    assert confirmation["simulated"] is True
