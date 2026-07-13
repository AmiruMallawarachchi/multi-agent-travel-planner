from __future__ import annotations

import httpx
import pytest

from mcp_servers.flight_mcp import serpapi_client as flight_client


API_KEY = "test-serpapi-key"
BASE_URL = "https://serpapi.test/search.json"


def make_client(handler: httpx.MockTransport) -> flight_client.SerpApiClient:
    return flight_client.SerpApiClient(
        api_key=API_KEY,
        base_url=BASE_URL,
        transport=handler,
    )


def option(token: str, airline: str = "Emirates") -> dict:
    return {
        "flights": [
            {
                "departure_airport": {
                    "name": "Bandaranaike International Airport",
                    "id": "CMB",
                    "time": "2026-08-01 10:05",
                },
                "arrival_airport": {
                    "name": "Dubai International Airport",
                    "id": "DXB",
                    "time": "2026-08-01 13:10",
                },
                "duration": 275,
                "airline": airline,
                "flight_number": "EK 649",
                "travel_class": "Economy",
                "airplane": "Boeing 777",
            }
        ],
        "layovers": [],
        "total_duration": 275,
        "price": 412,
        "booking_token": token,
    }


@pytest.mark.asyncio
async def test_round_trip_maps_params_and_normalizes_both_result_arrays():
    captured: dict[str, str] = {}
    best = option("best-token")
    best["flights"].append(
        {
            "departure_airport": {
                "name": "Dubai International Airport",
                "id": "DXB",
                "time": "2026-08-01 15:00",
            },
            "arrival_airport": {
                "name": "Heathrow Airport",
                "id": "LHR",
                "time": "2026-08-01 19:30",
            },
            "duration": 450,
            "airline": "Emirates",
            "flight_number": "EK 3",
            "travel_class": "Economy",
            "airplane": "Airbus A380",
        }
    )
    best["layovers"] = [
        {"id": "DXB", "name": "Dubai International Airport", "duration": 110}
    ]
    best["total_duration"] = 835

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(dict(request.url.params))
        return httpx.Response(
            200,
            json={
                "best_flights": [best],
                "other_flights": [option("other-token", "SriLankan Airlines")],
            },
        )

    results = await flight_client.search_flight_offers(
        departure_id="cmb",
        arrival_id="lhr",
        outbound_date="2026-08-01",
        return_date="2026-08-07",
        adults=2,
        children=1,
        travel_class=1,
        currency="usd",
        max_price=1500,
        client=make_client(httpx.MockTransport(handler)),
    )

    assert captured == {
        "engine": "google_flights",
        "departure_id": "CMB",
        "arrival_id": "LHR",
        "outbound_date": "2026-08-01",
        "type": "1",
        "adults": "2",
        "children": "1",
        "travel_class": "1",
        "currency": "USD",
        "return_date": "2026-08-07",
        "max_price": "1500",
        "api_key": API_KEY,
    }
    assert len(results) == 2
    assert results[0] == {
        "airline": "Emirates",
        "flight_number": "EK 649",
        "departure": {
            "airport_code": "CMB",
            "airport_name": "Bandaranaike International Airport",
            "time": "2026-08-01 10:05",
        },
        "arrival": {
            "airport_code": "LHR",
            "airport_name": "Heathrow Airport",
            "time": "2026-08-01 19:30",
        },
        "segments": [
            {
                "airline": "Emirates",
                "flight_number": "EK 649",
                "departure": {
                    "airport_code": "CMB",
                    "airport_name": "Bandaranaike International Airport",
                    "time": "2026-08-01 10:05",
                },
                "arrival": {
                    "airport_code": "DXB",
                    "airport_name": "Dubai International Airport",
                    "time": "2026-08-01 13:10",
                },
                "duration_minutes": 275,
                "travel_class": "Economy",
                "airplane": "Boeing 777",
            },
            {
                "airline": "Emirates",
                "flight_number": "EK 3",
                "departure": {
                    "airport_code": "DXB",
                    "airport_name": "Dubai International Airport",
                    "time": "2026-08-01 15:00",
                },
                "arrival": {
                    "airport_code": "LHR",
                    "airport_name": "Heathrow Airport",
                    "time": "2026-08-01 19:30",
                },
                "duration_minutes": 450,
                "travel_class": "Economy",
                "airplane": "Airbus A380",
            },
        ],
        "layovers": [
            {
                "airport_code": "DXB",
                "airport_name": "Dubai International Airport",
                "duration_minutes": 110,
            }
        ],
        "total_duration_minutes": 835,
        "price": 412,
        "currency": "USD",
        "travel_class": "Economy",
        "booking_token": "best-token",
    }
    assert results[1]["booking_token"] == "other-token"


@pytest.mark.asyncio
async def test_one_way_omits_optional_params_and_caps_combined_results_at_ten():
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(dict(request.url.params))
        return httpx.Response(
            200,
            json={
                "best_flights": [option(f"best-{index}") for index in range(6)],
                "other_flights": [option(f"other-{index}") for index in range(6)],
            },
        )

    results = await flight_client.search_flight_offers(
        "CMB",
        "DXB",
        "2026-08-01",
        client=make_client(httpx.MockTransport(handler)),
    )

    assert captured["type"] == "2"
    assert "return_date" not in captured
    assert "max_price" not in captured
    assert len(results) == 10
    assert [result["booking_token"] for result in results[-2:]] == [
        "other-2",
        "other-3",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"departure_id": "COLOMBO"}, "3-letter IATA"),
        ({"arrival_id": "CMB"}, "must be different"),
        ({"outbound_date": "2026-02-30"}, "valid calendar date"),
        ({"return_date": "2026-07-31"}, "after outbound_date"),
        ({"adults": 0}, "adults must be between"),
        ({"children": -1}, "children must be between"),
        ({"travel_class": 5}, "travel_class must be one of"),
        ({"currency": "US"}, "3-letter currency"),
        ({"max_price": 0}, "max_price must be greater"),
    ],
)
async def test_rejects_invalid_inputs_before_network(overrides: dict, message: str):
    def fail_if_called(_request: httpx.Request) -> httpx.Response:
        pytest.fail("network should not be called for invalid input")

    arguments = {
        "departure_id": "CMB",
        "arrival_id": "DXB",
        "outbound_date": "2026-08-01",
        "return_date": "2026-08-07",
        "adults": 1,
        "children": 0,
        "travel_class": 1,
        "currency": "USD",
        "max_price": None,
        "client": make_client(httpx.MockTransport(fail_if_called)),
    }
    arguments.update(overrides)

    with pytest.raises(flight_client.InvalidInputError, match=message):
        await flight_client.search_flight_offers(**arguments)


@pytest.mark.asyncio
async def test_missing_arrays_return_an_empty_list():
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200, json={"search_metadata": {"status": "Success"}}
        )
    )

    results = await flight_client.search_flight_offers(
        "CMB",
        "DXB",
        "2026-08-01",
        client=make_client(transport),
    )

    assert results == []


@pytest.mark.asyncio
async def test_provider_errors_redact_the_api_key():
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200, json={"error": f"Invalid API key: {API_KEY}"}
        )
    )

    with pytest.raises(flight_client.SerpApiError) as exc_info:
        await flight_client.search_flight_offers(
            "CMB",
            "DXB",
            "2026-08-01",
            client=make_client(transport),
        )

    assert API_KEY not in str(exc_info.value)
    assert "[redacted]" in str(exc_info.value)


@pytest.mark.asyncio
async def test_missing_api_key_fails_before_network():
    def fail_if_called(_request: httpx.Request) -> httpx.Response:
        pytest.fail("network should not be called without an API key")

    client = flight_client.SerpApiClient(
        api_key="",
        base_url=BASE_URL,
        transport=httpx.MockTransport(fail_if_called),
    )

    with pytest.raises(
        flight_client.SerpApiError, match="SERPAPI_API_KEY is not configured"
    ):
        await flight_client.search_flight_offers(
            "CMB", "DXB", "2026-08-01", client=client
        )


@pytest.mark.asyncio
async def test_timeout_is_wrapped_without_leaking_the_request_url():
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(flight_client.SerpApiError) as exc_info:
        await flight_client.search_flight_offers(
            "CMB",
            "DXB",
            "2026-08-01",
            client=make_client(httpx.MockTransport(timeout)),
        )

    assert str(exc_info.value) == "SerpApi request timed out"
    assert API_KEY not in str(exc_info.value)


@pytest.mark.asyncio
async def test_booking_remains_explicitly_simulated():
    confirmation = await flight_client.book_flight_offer("booking-token", "Asha Perera")

    assert confirmation["confirmation_number"].startswith("TW-F-")
    assert confirmation["offer_id"] == "booking-token"
    assert confirmation["traveller_name"] == "Asha Perera"
    assert confirmation["simulated"] is True
