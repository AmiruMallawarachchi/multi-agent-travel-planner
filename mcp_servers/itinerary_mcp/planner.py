"""Deterministic itinerary construction and validation."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

MAX_TRIP_DAYS = 21
MAX_ACTIVITIES = 60
MAX_INTERESTS = 10

_PACE_SLOTS = {
    "relaxed": ("morning", "afternoon"),
    "balanced": ("morning", "afternoon", "evening"),
    "active": ("early morning", "late morning", "afternoon", "evening"),
}


class InvalidInputError(ValueError):
    """Itinerary input is invalid and no plan should be produced."""


def _text(label: str, value: Any, *, maximum: int) -> str:
    normalized = " ".join(str(value or "").split())
    if not normalized:
        raise InvalidInputError(f"{label} is required")
    if len(normalized) > maximum:
        raise InvalidInputError(f"{label} must be {maximum} characters or fewer")
    return normalized


def _date(label: str, value: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise InvalidInputError(
            f"{label} must be a valid calendar date in YYYY-MM-DD format"
        ) from None


def _integer(label: str, value: int, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        raise InvalidInputError(f"{label} must be between {minimum} and {maximum}")
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        raise InvalidInputError(
            f"{label} must be between {minimum} and {maximum}"
        ) from None
    if isinstance(value, float) and not value.is_integer():
        raise InvalidInputError(f"{label} must be between {minimum} and {maximum}")
    if not minimum <= normalized <= maximum:
        raise InvalidInputError(f"{label} must be between {minimum} and {maximum}")
    return normalized


def _budget(value: float | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise InvalidInputError("budget must be greater than zero")
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        raise InvalidInputError("budget must be greater than zero") from None
    if normalized <= 0 or normalized > 1_000_000_000:
        raise InvalidInputError("budget must be greater than zero and reasonable")
    return round(normalized, 2)


def _interests(values: list[str] | None) -> list[str]:
    if not values:
        return ["local highlights"]
    if len(values) > MAX_INTERESTS:
        raise InvalidInputError(f"interests must contain at most {MAX_INTERESTS} items")
    normalized: list[str] = []
    for value in values:
        interest = _text("interest", value, maximum=50)
        if interest.casefold() not in {item.casefold() for item in normalized}:
            normalized.append(interest)
    return normalized


def _coordinates(raw: dict[str, Any]) -> dict[str, float] | None:
    latitude = raw.get("latitude")
    longitude = raw.get("longitude")
    if latitude is None and longitude is None:
        return None
    if latitude is None or longitude is None:
        raise InvalidInputError(
            "activity latitude and longitude must be provided together"
        )
    try:
        latitude_value = float(latitude)
        longitude_value = float(longitude)
    except (TypeError, ValueError):
        raise InvalidInputError("activity coordinates must be numbers") from None
    if not -90 <= latitude_value <= 90 or not -180 <= longitude_value <= 180:
        raise InvalidInputError("activity coordinates are outside valid ranges")
    return {"latitude": latitude_value, "longitude": longitude_value}


def _activities(values: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not values:
        return []
    if len(values) > MAX_ACTIVITIES:
        raise InvalidInputError(
            f"activities must contain at most {MAX_ACTIVITIES} items"
        )

    normalized: list[dict[str, Any]] = []
    for raw in values:
        if not isinstance(raw, dict):
            raise InvalidInputError("each activity must be an object")
        name = _text("activity name", raw.get("name"), maximum=160)
        duration = _integer(
            "activity duration_minutes", raw.get("duration_minutes", 120), 30, 720
        )
        normalized.append(
            {
                "name": name,
                "category": " ".join(str(raw.get("category") or "general").split())[
                    :50
                ],
                "duration_minutes": duration,
                "address": " ".join(str(raw.get("address") or "").split()) or None,
                "coordinates": _coordinates(raw),
                "source_url": str(raw.get("source_url") or "").strip() or None,
                "is_placeholder": False,
            }
        )
    return normalized


def _placeholder(
    *, destination: str, interest: str, slot: str, day_number: int
) -> dict[str, Any]:
    return {
        "name": f"{interest.title()} planning block in {destination}",
        "category": interest,
        "duration_minutes": 120,
        "address": None,
        "coordinates": None,
        "source_url": None,
        "is_placeholder": True,
        "time_slot": slot,
        "day_number": day_number,
    }


def create_itinerary_plan(
    destination: str,
    start_date: str,
    end_date: str,
    travelers: int = 1,
    interests: list[str] | None = None,
    pace: str = "balanced",
    budget: float | None = None,
    activities: list[dict[str, Any]] | None = None,
    budget_currency: str | None = None,
) -> dict[str, Any]:
    """Build a bounded, structured itinerary without inventing venue facts."""
    destination = _text("destination", destination, maximum=120)
    start = _date("start_date", start_date)
    end = _date("end_date", end_date)
    if end < start:
        raise InvalidInputError("end_date must be on or after start_date")
    duration_days = (end - start).days + 1
    if duration_days > MAX_TRIP_DAYS:
        raise InvalidInputError(f"trip duration must not exceed {MAX_TRIP_DAYS} days")

    travelers = _integer("travelers", travelers, 1, 20)
    normalized_pace = str(pace or "").strip().casefold()
    if normalized_pace not in _PACE_SLOTS:
        raise InvalidInputError("pace must be one of relaxed, balanced, or active")
    normalized_interests = _interests(interests)
    normalized_activities = _activities(activities)
    normalized_budget = _budget(budget)

    if budget_currency is not None:
        normalized_currency = str(budget_currency).strip().upper()
        if len(normalized_currency) != 3 or not normalized_currency.isalpha():
            raise InvalidInputError("budget_currency must be a 3-letter currency code")
    else:
        normalized_currency = None

    slots = _PACE_SLOTS[normalized_pace]
    activity_index = 0
    days: list[dict[str, Any]] = []
    for offset in range(duration_days):
        day_date = start + timedelta(days=offset)
        day_number = offset + 1
        items: list[dict[str, Any]] = []
        for slot_index, slot in enumerate(slots):
            if normalized_activities:
                if activity_index >= len(normalized_activities):
                    break
                item = {
                    **normalized_activities[activity_index],
                    "time_slot": slot,
                    "day_number": day_number,
                }
                activity_index += 1
            else:
                interest = normalized_interests[
                    (offset * len(slots) + slot_index) % len(normalized_interests)
                ]
                item = _placeholder(
                    destination=destination,
                    interest=interest,
                    slot=slot,
                    day_number=day_number,
                )
            items.append(item)
        days.append(
            {
                "day_number": day_number,
                "date": day_date.isoformat(),
                "title": f"Day {day_number} in {destination}",
                "items": items,
            }
        )

    unscheduled = normalized_activities[activity_index:]
    budget_summary = None
    if normalized_budget is not None:
        budget_summary = {
            "total": normalized_budget,
            "per_day": round(normalized_budget / duration_days, 2),
            "per_traveler": round(normalized_budget / travelers, 2),
            "currency": normalized_currency,
        }

    return {
        "destination": destination,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "duration_days": duration_days,
        "travelers": travelers,
        "interests": normalized_interests,
        "pace": normalized_pace,
        "budget": budget_summary,
        "source": "provided_activities"
        if normalized_activities
        else "planning_framework",
        "days": days,
        "unscheduled_activities": unscheduled,
        "disclaimer": (
            "Confirm specific venues, opening hours, travel times, prices, and "
            "availability before relying on this itinerary."
        ),
    }
