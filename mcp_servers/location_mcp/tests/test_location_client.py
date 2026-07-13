from __future__ import annotations

import httpx
import pytest

from mcp_servers.location_mcp import location_client


API_KEY = "test-location-serpapi-key"
GEOCODING_URL = "https://geo.test/v1/search"
SERPAPI_URL = "https://maps.test/search.json"


def make_client(handler, *, api_key: str = API_KEY) -> location_client.LocationClient:
    transport = (
        handler
        if isinstance(handler, httpx.MockTransport)
        else httpx.MockTransport(handler)
    )
    return location_client.LocationClient(
        api_key=api_key,
        geocoding_url=GEOCODING_URL,
        serpapi_url=SERPAPI_URL,
        transport=transport,
    )


def geocoding_payload() -> dict:
    return {
        "results": [
            {
                "id": 292223,
                "name": "Dubai",
                "latitude": 25.0772,
                "longitude": 55.3093,
                "elevation": 3,
                "country": "United Arab Emirates",
                "country_code": "AE",
                "admin1": "Dubai",
                "timezone": "Asia/Dubai",
                "population": 3478300,
            }
        ]
    }


def maps_payload() -> dict:
    return {
        "local_results": [
            {
                "position": 1,
                "title": "Museum of the Future",
                "type": "Museum",
                "address": "Sheikh Zayed Road, Dubai",
                "rating": 4.5,
                "reviews": 52000,
                "phone": "+971 800 2071",
                "website": "https://museumofthefuture.ae",
                "gps_coordinates": {"latitude": 25.2192, "longitude": 55.2821},
                "open_state": "Open",
                "thumbnail": "https://images.test/museum.jpg",
                "place_id": "place-1",
                "data_id": "data-1",
            }
        ]
    }


@pytest.mark.asyncio
async def test_resolves_location_and_normalizes_geocoding_results():
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(dict(request.url.params))
        return httpx.Response(200, json=geocoding_payload())

    results = await location_client.resolve_locations(
        "Dubai", count=3, client=make_client(handler)
    )

    assert captured == {
        "name": "Dubai",
        "count": "3",
        "language": "en",
        "format": "json",
    }
    assert results == [
        {
            "name": "Dubai",
            "country": "United Arab Emirates",
            "country_code": "AE",
            "region": "Dubai",
            "latitude": 25.0772,
            "longitude": 55.3093,
            "timezone": "Asia/Dubai",
            "elevation_meters": 3,
            "population": 3478300,
        }
    ]


@pytest.mark.asyncio
async def test_search_places_resolves_near_location_and_maps_results():
    captured: list[tuple[str, dict[str, str]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append((request.url.host, dict(request.url.params)))
        if request.url.host == "geo.test":
            return httpx.Response(200, json=geocoding_payload())
        return httpx.Response(200, json=maps_payload())

    results = await location_client.search_places(
        query="museums",
        near="Dubai",
        zoom=14,
        client=make_client(handler),
    )

    assert captured[1] == (
        "maps.test",
        {
            "engine": "google_maps",
            "q": "museums near Dubai",
            "type": "search",
            "hl": "en",
            "ll": "@25.0772,55.3093,14z",
            "api_key": API_KEY,
        },
    )
    assert results[0]["name"] == "Museum of the Future"
    assert results[0]["coordinates"] == {"latitude": 25.2192, "longitude": 55.2821}
    assert results[0]["data_id"] == "data-1"


@pytest.mark.asyncio
async def test_explicit_coordinates_skip_geocoding():
    hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        hosts.append(request.url.host or "")
        return httpx.Response(200, json=maps_payload())

    await location_client.search_places(
        "cafes",
        latitude=6.9271,
        longitude=79.8612,
        client=make_client(handler),
    )

    assert hosts == ["maps.test"]


@pytest.mark.asyncio
async def test_missing_local_results_returns_empty_list():
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200, json={"search_metadata": {"status": "Success"}}
        )
    )

    results = await location_client.search_places(
        "museums", client=make_client(transport)
    )

    assert results == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("function_name", "overrides", "message"),
    [
        ("resolve", {"query": ""}, "query"),
        ("resolve", {"count": 11}, "count"),
        ("search", {"query": ""}, "query"),
        ("search", {"latitude": 91, "longitude": 0}, "latitude"),
        ("search", {"latitude": 10, "longitude": None}, "provided together"),
        ("search", {"zoom": 22}, "zoom"),
    ],
)
async def test_rejects_invalid_inputs_before_network(
    function_name: str, overrides: dict, message: str
):
    def fail_if_called(_request: httpx.Request) -> httpx.Response:
        pytest.fail("network should not be called")

    client = make_client(fail_if_called)
    with pytest.raises(location_client.InvalidInputError, match=message):
        if function_name == "resolve":
            await location_client.resolve_locations(client=client, **overrides)
        else:
            arguments = {
                "query": "museums",
                "near": None,
                "latitude": None,
                "longitude": None,
                "zoom": 13,
                "client": client,
            }
            arguments.update(overrides)
            await location_client.search_places(**arguments)


@pytest.mark.asyncio
async def test_missing_api_key_fails_before_maps_request():
    def fail_if_called(_request: httpx.Request) -> httpx.Response:
        pytest.fail("network should not be called without a key")

    with pytest.raises(location_client.LocationProviderError, match="SERPAPI_API_KEY"):
        await location_client.search_places(
            "museums", client=make_client(fail_if_called, api_key="")
        )


@pytest.mark.asyncio
async def test_provider_error_redacts_api_key():
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            429, json={"error": f"Quota exceeded for {API_KEY}"}
        )
    )

    with pytest.raises(location_client.LocationProviderError) as exc_info:
        await location_client.search_places("museums", client=make_client(transport))

    assert API_KEY not in str(exc_info.value)
    assert "[redacted]" in str(exc_info.value)
