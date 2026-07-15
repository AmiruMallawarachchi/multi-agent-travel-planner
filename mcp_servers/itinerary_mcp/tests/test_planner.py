from __future__ import annotations

import pytest

from mcp_servers.itinerary_mcp import planner


def test_builds_structured_itinerary_from_supplied_activities():
    result = planner.create_itinerary_plan(
        destination="Tokyo",
        start_date="2027-04-10",
        end_date="2027-04-12",
        travelers=2,
        interests=["food", "culture"],
        pace="balanced",
        budget=3000,
        activities=[
            {
                "name": "Tsukiji outer market",
                "category": "food",
                "duration_minutes": 120,
                "address": "Tsukiji, Tokyo",
            },
            {
                "name": "Tokyo National Museum",
                "category": "culture",
                "duration_minutes": 150,
            },
        ],
    )

    assert result["destination"] == "Tokyo"
    assert result["duration_days"] == 3
    assert result["travelers"] == 2
    assert result["budget"] == {
        "total": 3000.0,
        "per_day": 1000.0,
        "per_traveler": 1500.0,
        "currency": None,
    }
    assert result["source"] == "provided_activities"
    assert [day["date"] for day in result["days"]] == [
        "2027-04-10",
        "2027-04-11",
        "2027-04-12",
    ]
    assert result["days"][0]["items"][0]["name"] == "Tsukiji outer market"
    assert result["days"][0]["items"][1]["name"] == "Tokyo National Museum"
    assert result["unscheduled_activities"] == []


def test_builds_honest_planning_framework_without_place_results():
    result = planner.create_itinerary_plan(
        destination="Lisbon",
        start_date="2027-05-01",
        end_date="2027-05-02",
        interests=["food", "architecture"],
        pace="relaxed",
    )

    assert result["source"] == "planning_framework"
    assert len(result["days"]) == 2
    assert all(len(day["items"]) == 2 for day in result["days"])
    assert all(
        item["is_placeholder"] for day in result["days"] for item in day["items"]
    )
    assert "Confirm specific venues" in result["disclaimer"]


def test_overflow_activities_are_returned_instead_of_silently_dropped():
    activities = [{"name": f"Place {index}"} for index in range(5)]

    result = planner.create_itinerary_plan(
        "Kandy",
        "2027-06-01",
        "2027-06-01",
        pace="relaxed",
        activities=activities,
    )

    assert [item["name"] for item in result["days"][0]["items"]] == [
        "Place 0",
        "Place 1",
    ]
    assert [item["name"] for item in result["unscheduled_activities"]] == [
        "Place 2",
        "Place 3",
        "Place 4",
    ]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"destination": "  "}, "destination"),
        ({"start_date": "2027-02-30"}, "valid calendar date"),
        ({"end_date": "2027-03-31"}, "on or after start_date"),
        ({"end_date": "2027-05-10"}, "21 days"),
        ({"travelers": 0}, "travelers must be between"),
        ({"pace": "rushed"}, "pace must be one of"),
        ({"budget": 0}, "budget must be greater"),
        ({"activities": [{"name": ""}]}, "activity name"),
    ],
)
def test_rejects_invalid_plan_inputs(overrides: dict, message: str):
    arguments = {
        "destination": "Tokyo",
        "start_date": "2027-04-10",
        "end_date": "2027-04-12",
        "travelers": 1,
        "interests": [],
        "pace": "balanced",
        "budget": None,
        "activities": [],
    }
    arguments.update(overrides)

    with pytest.raises(planner.InvalidInputError, match=message):
        planner.create_itinerary_plan(**arguments)
