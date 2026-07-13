from __future__ import annotations

import pytest

from mcp_servers.flight_mcp import amadeus_client as flight_client
from mcp_servers.hotel_mcp import amadeus_client as hotel_client


class TestHotelClientValidation:
    @pytest.mark.asyncio
    async def test_rejects_invalid_calendar_dates_before_network(self):
        with pytest.raises(hotel_client.InvalidInputError, match="valid calendar date"):
            await hotel_client.search_hotel_offers("PAR", "2026-02-30", "2026-03-02")

    @pytest.mark.asyncio
    async def test_rejects_checkout_before_or_equal_to_checkin(self):
        with pytest.raises(hotel_client.InvalidInputError, match="check_out must be after check_in"):
            await hotel_client.search_hotel_offers("PAR", "2026-09-10", "2026-09-10")

    @pytest.mark.asyncio
    async def test_rejects_invalid_adult_count(self):
        with pytest.raises(hotel_client.InvalidInputError, match="between 1 and 9"):
            await hotel_client.search_hotel_offers("PAR", "2026-09-10", "2026-09-14", adults=10)

    @pytest.mark.asyncio
    async def test_search_hotel_offers_maps_validated_params_to_amadeus(self, monkeypatch):
        captured = {}

        async def fake_list_hotels_by_city(city_code: str, limit: int = 20):
            captured["list"] = {"city_code": city_code, "limit": limit}
            return [{"hotelId": "H1"}, {"hotelId": "H2"}]

        async def fake_get(path: str, params: dict):
            captured["get"] = {"path": path, "params": params}
            return {"data": [{"id": "offer-1"}, {"id": "offer-2"}]}

        monkeypatch.setattr(hotel_client, "list_hotels_by_city", fake_list_hotels_by_city)
        monkeypatch.setattr(hotel_client, "_get", fake_get)

        offers = await hotel_client.search_hotel_offers("par", "2026-09-10", "2026-09-14", adults=2)

        assert offers == [{"id": "offer-1"}, {"id": "offer-2"}]
        assert captured["list"] == {"city_code": "PAR", "limit": 20}
        assert captured["get"] == {
            "path": "/v3/shopping/hotel-offers",
            "params": {
                "hotelIds": "H1,H2",
                "checkInDate": "2026-09-10",
                "checkOutDate": "2026-09-14",
                "adults": 2,
            },
        }


class TestFlightClientValidation:
    @pytest.mark.asyncio
    async def test_rejects_invalid_calendar_departure_date_before_network(self):
        with pytest.raises(flight_client.InvalidInputError, match="valid calendar date"):
            await flight_client.search_flight_offers("CMB", "LHR", "2026-02-30")

    @pytest.mark.asyncio
    async def test_rejects_invalid_adult_count(self):
        with pytest.raises(flight_client.InvalidInputError, match="between 1 and 9"):
            await flight_client.search_flight_offers("CMB", "LHR", "2026-09-01", adults=0)

    @pytest.mark.asyncio
    async def test_search_flight_offers_maps_validated_params_to_amadeus(self, monkeypatch):
        captured = {}

        async def fake_get(path: str, params: dict):
            captured["get"] = {"path": path, "params": params}
            return {"data": [{"id": "flight-offer-1"}]}

        monkeypatch.setattr(flight_client, "_get", fake_get)

        offers = await flight_client.search_flight_offers("cmb", "lhr", "2026-09-01", adults=2)

        assert offers == [{"id": "flight-offer-1"}]
        assert captured["get"] == {
            "path": "/v2/shopping/flight-offers",
            "params": {
                "originLocationCode": "CMB",
                "destinationLocationCode": "LHR",
                "departureDate": "2026-09-01",
                "adults": 2,
                "max": 5,
                "currencyCode": "USD",
            },
        }
