"""In-process tool adapters for single-service demo deployments.

The production architecture keeps provider clients behind MCP services. Render
Free is better suited to one backend service, so this module exposes the same
tool names from the backend process when TRIPWEAVER_TOOL_MODE=local.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from langchain_core.tools import StructuredTool

from mcp_servers.currency_mcp.frankfurter_client import (
    CurrencyProviderError,
    InvalidInputError as CurrencyInputError,
    convert_currency as convert_reference_currency,
    get_exchange_rate as fetch_exchange_rate,
    list_supported_currencies as fetch_supported_currencies,
)
from mcp_servers.flight_mcp.serpapi_client import (
    InvalidInputError as FlightInputError,
    SerpApiError as FlightProviderError,
    book_flight_offer,
    list_flights as list_provider_flights,
    search_flight_offers,
)
from mcp_servers.hotel_mcp.serpapi_client import (
    InvalidInputError as HotelInputError,
    SerpApiError as HotelProviderError,
    book_hotel_offer,
    list_hotels as list_provider_hotels,
    search_hotel_properties,
)
from mcp_servers.itinerary_mcp.planner import (
    InvalidInputError as ItineraryInputError,
    create_itinerary_plan,
)
from mcp_servers.location_mcp.location_client import (
    InvalidInputError as LocationInputError,
    LocationProviderError,
    resolve_locations,
    search_places as search_provider_places,
)
from mcp_servers.weather_mcp.open_meteo_client import (
    InvalidInputError as WeatherInputError,
    WeatherProviderError,
    get_weather_forecast as fetch_weather_forecast,
)


async def list_hotels(destination: str) -> dict[str, Any]:
    """List hotels using a one-night stay beginning tomorrow."""
    try:
        hotels = await list_provider_hotels(destination)
        return {"ok": True, "hotels": hotels}
    except HotelInputError as exc:
        return {"ok": False, "error": str(exc)}
    except HotelProviderError as exc:
        return {"ok": False, "error": f"Hotel service unavailable: {exc}"}


async def search_hotels(
    destination: str,
    check_in_date: str,
    check_out_date: str,
    adults: int = 2,
    children: int = 0,
    currency: str = "USD",
    min_price: int | None = None,
    max_price: int | None = None,
    rating: int | None = None,
) -> dict[str, Any]:
    """Search priced, available hotel offers."""
    try:
        offers = await search_hotel_properties(
            destination=destination,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            adults=adults,
            children=children,
            currency=currency,
            min_price=min_price,
            max_price=max_price,
            rating=rating,
        )
        return {"ok": True, "offers": offers}
    except HotelInputError as exc:
        return {"ok": False, "error": str(exc)}
    except HotelProviderError as exc:
        return {"ok": False, "error": f"Hotel service unavailable: {exc}"}


async def book_hotel(offer_id: str, guest_name: str) -> dict[str, Any]:
    """Book a specific hotel offer returned by search_hotels."""
    try:
        confirmation = await book_hotel_offer(offer_id, guest_name)
        return {"ok": True, "confirmation": confirmation}
    except HotelInputError as exc:
        return {"ok": False, "error": str(exc)}


async def list_flights(departure_id: str, arrival_id: str) -> dict[str, Any]:
    """List flights operating on a route, as a lightweight overview."""
    try:
        flights = await list_provider_flights(departure_id, arrival_id)
        return {"ok": True, "flights": flights}
    except FlightInputError as exc:
        return {"ok": False, "error": str(exc)}
    except FlightProviderError as exc:
        return {"ok": False, "error": f"Flight service unavailable: {exc}"}


async def search_flights(
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    return_date: str | None = None,
    adults: int = 1,
    children: int = 0,
    travel_class: int = 1,
    currency: str = "USD",
    max_price: int | None = None,
) -> dict[str, Any]:
    """Search priced, available flight offers for a route and date."""
    try:
        offers = await search_flight_offers(
            departure_id=departure_id,
            arrival_id=arrival_id,
            outbound_date=outbound_date,
            return_date=return_date,
            adults=adults,
            children=children,
            travel_class=travel_class,
            currency=currency,
            max_price=max_price,
        )
        return {"ok": True, "offers": offers}
    except FlightInputError as exc:
        return {"ok": False, "error": str(exc)}
    except FlightProviderError as exc:
        return {"ok": False, "error": f"Flight service unavailable: {exc}"}


async def book_flight(offer_id: str, traveller_name: str) -> dict[str, Any]:
    """Book a specific flight offer returned by search_flights."""
    try:
        confirmation = await book_flight_offer(offer_id, traveller_name)
        return {"ok": True, "confirmation": confirmation}
    except FlightInputError as exc:
        return {"ok": False, "error": str(exc)}


async def create_itinerary(
    destination: str,
    start_date: str,
    end_date: str,
    travelers: int = 1,
    interests: list[str] | None = None,
    pace: str = "balanced",
    budget: float | None = None,
    budget_currency: str | None = None,
    activities: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a structured itinerary from trip details and optional place results."""
    try:
        itinerary = create_itinerary_plan(
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            travelers=travelers,
            interests=interests,
            pace=pace,
            budget=budget,
            budget_currency=budget_currency,
            activities=activities,
        )
        return {"ok": True, "itinerary": itinerary}
    except ItineraryInputError as exc:
        return {"ok": False, "error": str(exc)}


async def _weather_result(**arguments: Any) -> dict[str, Any]:
    try:
        weather = await fetch_weather_forecast(**arguments)
        return {"ok": True, "weather": weather}
    except WeatherInputError as exc:
        return {"ok": False, "error": str(exc)}
    except WeatherProviderError as exc:
        return {"ok": False, "error": f"Weather service unavailable: {exc}"}


async def get_current_weather(
    location: str,
    temperature_unit: str = "celsius",
    wind_speed_unit: str = "kmh",
    precipitation_unit: str = "mm",
) -> dict[str, Any]:
    """Get current weather for a city or place name."""
    result = await _weather_result(
        location=location,
        forecast_days=1,
        temperature_unit=temperature_unit,
        wind_speed_unit=wind_speed_unit,
        precipitation_unit=precipitation_unit,
    )
    if result.get("ok"):
        weather = result["weather"]
        result["weather"] = {
            "location": weather["location"],
            "timezone": weather["timezone"],
            "current": weather["current"],
            "source": weather["source"],
        }
    return result


async def get_weather_forecast(
    location: str,
    forecast_days: int = 7,
    start_date: str | None = None,
    end_date: str | None = None,
    temperature_unit: str = "celsius",
    wind_speed_unit: str = "kmh",
    precipitation_unit: str = "mm",
) -> dict[str, Any]:
    """Get up to 16 days of current and daily weather for a place."""
    return await _weather_result(
        location=location,
        forecast_days=forecast_days,
        start_date=start_date,
        end_date=end_date,
        temperature_unit=temperature_unit,
        wind_speed_unit=wind_speed_unit,
        precipitation_unit=precipitation_unit,
    )


async def _currency_result(
    operation: Callable[..., Awaitable[Any]], **arguments: Any
) -> dict[str, Any]:
    try:
        return {"ok": True, "result": await operation(**arguments)}
    except CurrencyInputError as exc:
        return {"ok": False, "error": str(exc)}
    except CurrencyProviderError as exc:
        return {"ok": False, "error": f"Currency service unavailable: {exc}"}


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


async def list_supported_currencies() -> dict[str, Any]:
    """List currencies supported by the reference-rate provider."""
    return await _currency_result(fetch_supported_currencies)


def _location_failure(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, LocationInputError):
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "error": f"Location service unavailable: {exc}"}


async def resolve_location(query: str, count: int = 5) -> dict[str, Any]:
    """Resolve a city or place name to coordinates and timezone metadata."""
    try:
        return {"ok": True, "locations": await resolve_locations(query, count=count)}
    except (LocationInputError, LocationProviderError) as exc:
        return _location_failure(exc)


async def search_places(
    query: str,
    near: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    zoom: int = 13,
) -> dict[str, Any]:
    """Search attractions, restaurants, and other local places."""
    try:
        places = await search_provider_places(
            query,
            near=near,
            latitude=latitude,
            longitude=longitude,
            zoom=zoom,
        )
        return {"ok": True, "places": places}
    except (LocationInputError, LocationProviderError) as exc:
        return _location_failure(exc)


def _tool(coroutine: Callable[..., Awaitable[dict[str, Any]]]) -> StructuredTool:
    return StructuredTool.from_function(
        coroutine=coroutine,
        name=coroutine.__name__,
        description=(coroutine.__doc__ or coroutine.__name__).strip(),
    )


LOCAL_TOOLS: dict[str, list[StructuredTool]] = {
    "hotel-mcp": [_tool(list_hotels), _tool(search_hotels), _tool(book_hotel)],
    "flight-mcp": [_tool(list_flights), _tool(search_flights), _tool(book_flight)],
    "itinerary-mcp": [_tool(create_itinerary)],
    "weather-mcp": [_tool(get_current_weather), _tool(get_weather_forecast)],
    "currency-mcp": [
        _tool(convert_currency),
        _tool(get_exchange_rate),
        _tool(list_supported_currencies),
    ],
    "location-mcp": [_tool(resolve_location), _tool(search_places)],
}


def get_local_tools_for(server: str) -> list[StructuredTool]:
    return LOCAL_TOOLS.get(server, [])

