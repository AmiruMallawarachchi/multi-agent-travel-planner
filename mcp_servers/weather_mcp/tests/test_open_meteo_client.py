from __future__ import annotations

import httpx
import pytest

from mcp_servers.weather_mcp import open_meteo_client as weather_client


GEOCODING_URL = "https://geo.test/v1/search"
FORECAST_URL = "https://weather.test/v1/forecast"


def make_client(handler) -> weather_client.OpenMeteoClient:
    transport = (
        handler
        if isinstance(handler, httpx.MockTransport)
        else httpx.MockTransport(handler)
    )
    return weather_client.OpenMeteoClient(
        geocoding_url=GEOCODING_URL,
        forecast_url=FORECAST_URL,
        transport=transport,
    )


def geocoding_payload() -> dict:
    return {
        "results": [
            {
                "id": 1850147,
                "name": "Tokyo",
                "latitude": 35.6895,
                "longitude": 139.6917,
                "country": "Japan",
                "country_code": "JP",
                "admin1": "Tokyo",
                "timezone": "Asia/Tokyo",
            }
        ]
    }


def forecast_payload() -> dict:
    return {
        "timezone": "Asia/Tokyo",
        "current": {
            "time": "2027-04-10T09:00",
            "temperature_2m": 18.4,
            "apparent_temperature": 17.8,
            "precipitation": 0.0,
            "weather_code": 1,
            "cloud_cover": 20,
            "wind_speed_10m": 8.2,
        },
        "current_units": {
            "temperature_2m": "°C",
            "apparent_temperature": "°C",
            "precipitation": "mm",
            "wind_speed_10m": "km/h",
        },
        "daily": {
            "time": ["2027-04-10", "2027-04-11"],
            "weather_code": [1, 61],
            "temperature_2m_max": [21.0, 17.0],
            "temperature_2m_min": [13.0, 11.0],
            "precipitation_probability_max": [10, 75],
            "sunrise": ["2027-04-10T05:15", "2027-04-11T05:14"],
            "sunset": ["2027-04-10T18:10", "2027-04-11T18:11"],
        },
        "daily_units": {
            "temperature_2m_max": "°C",
            "temperature_2m_min": "°C",
            "precipitation_probability_max": "%",
        },
    }


@pytest.mark.asyncio
async def test_maps_requests_and_normalizes_forecast():
    captured: list[tuple[str, dict[str, str]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append((request.url.host, dict(request.url.params)))
        if request.url.host == "geo.test":
            return httpx.Response(200, json=geocoding_payload())
        return httpx.Response(200, json=forecast_payload())

    result = await weather_client.get_weather_forecast(
        location="Tokyo",
        start_date="2027-04-10",
        end_date="2027-04-11",
        temperature_unit="celsius",
        client=make_client(handler),
    )

    assert captured[0] == (
        "geo.test",
        {"name": "Tokyo", "count": "1", "language": "en", "format": "json"},
    )
    assert captured[1][1]["latitude"] == "35.6895"
    assert captured[1][1]["longitude"] == "139.6917"
    assert captured[1][1]["start_date"] == "2027-04-10"
    assert captured[1][1]["end_date"] == "2027-04-11"
    assert "temperature_2m" in captured[1][1]["current"]
    assert result["location"]["name"] == "Tokyo"
    assert result["current"]["weather"] == "Mainly clear"
    assert result["daily"][1]["weather"] == "Slight rain"
    assert result["daily"][1]["precipitation_probability_max"] == 75


@pytest.mark.asyncio
async def test_uses_forecast_days_when_dates_are_not_supplied():
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "geo.test":
            return httpx.Response(200, json=geocoding_payload())
        captured.update(dict(request.url.params))
        return httpx.Response(200, json=forecast_payload())

    await weather_client.get_weather_forecast(
        "Tokyo", forecast_days=5, client=make_client(handler)
    )

    assert captured["forecast_days"] == "5"
    assert "start_date" not in captured


@pytest.mark.asyncio
async def test_unknown_location_is_a_controlled_error():
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, json={"results": []})
    )

    with pytest.raises(weather_client.LocationNotFoundError, match="No location found"):
        await weather_client.get_weather_forecast(
            "Atlantis", client=make_client(transport)
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"location": ""}, "location"),
        ({"forecast_days": 17}, "forecast_days"),
        ({"start_date": "2027-02-30", "end_date": "2027-03-01"}, "valid calendar date"),
        (
            {"start_date": "2027-04-12", "end_date": "2027-04-10"},
            "on or after start_date",
        ),
        ({"start_date": "2027-04-01", "end_date": "2027-04-20"}, "16 days"),
        ({"temperature_unit": "kelvin"}, "temperature_unit"),
    ],
)
async def test_rejects_invalid_inputs_before_network(overrides: dict, message: str):
    def fail_if_called(_request: httpx.Request) -> httpx.Response:
        pytest.fail("network should not be called")

    arguments = {
        "location": "Tokyo",
        "forecast_days": 7,
        "start_date": None,
        "end_date": None,
        "temperature_unit": "celsius",
        "client": make_client(fail_if_called),
    }
    arguments.update(overrides)

    with pytest.raises(weather_client.InvalidInputError, match=message):
        await weather_client.get_weather_forecast(**arguments)


@pytest.mark.asyncio
async def test_timeout_is_wrapped_without_request_details():
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(weather_client.WeatherProviderError) as exc_info:
        await weather_client.get_weather_forecast("Tokyo", client=make_client(timeout))

    assert str(exc_info.value) == "Weather provider request timed out"
    assert GEOCODING_URL not in str(exc_info.value)
