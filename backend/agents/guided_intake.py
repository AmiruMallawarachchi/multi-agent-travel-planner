"""Deterministic guided-intake flows used by TripWeaver agents."""

from __future__ import annotations

from typing import TypedDict

from langchain_core.messages import AIMessage

from agents.entity import GuidedIntake


class IntakeQuestion(TypedDict):
    id: str
    answer_key: str
    prompt: str
    options: tuple[tuple[str, str], ...]


TRIP_BUDGET_QUESTIONS: tuple[IntakeQuestion, ...] = (
    {
        "id": "trip-budget-origin-currency",
        "answer_key": "origin_currency",
        "prompt": (
            "Where are you travelling from, and which currency should I use "
            "for the estimate?"
        ),
        "options": (
            ("Sri Lanka (LKR)", "I am travelling from Sri Lanka; use LKR."),
            ("India (INR)", "I am travelling from India; use INR."),
            (
                "United States (USD)",
                "I am travelling from the United States; use USD.",
            ),
            ("Singapore (SGD)", "Use Singapore dollars (SGD)."),
        ),
    },
    {
        "id": "trip-budget-expenses",
        "answer_key": "expense_scope",
        "prompt": "Which expenses should the one-week estimate include?",
        "options": (
            (
                "Complete trip",
                "Include flights, accommodation, food, local transport, and activities.",
            ),
            (
                "Stay and daily costs",
                "Include accommodation, food, local transport, and activities, but not flights.",
            ),
            ("Flights and accommodation", "Include flights and accommodation only."),
            ("Daily spending", "Include food, local transport, and activities only."),
        ),
    },
    {
        "id": "trip-budget-style",
        "answer_key": "budget_style",
        "prompt": "What budget level should I use for each included category?",
        "options": (
            (
                "Compare all levels",
                "I have no fixed budget; compare budget, mid-range, and premium totals.",
            ),
            (
                "Budget-friendly",
                "Use budget-friendly estimates for each category.",
            ),
            (
                "Comfortable mid-range",
                "Use comfortable mid-range estimates for each category.",
            ),
            ("Premium", "Use premium estimates for each category."),
        ),
    },
)


def message_content(message: object) -> str:
    if isinstance(message, dict):
        return str(message.get("content", ""))
    return str(getattr(message, "content", ""))


def is_trip_budget_request(message: str) -> bool:
    normalized = " ".join(message.lower().split())
    travel_terms = ("travel", "trip", "visit", "vacation", "holiday")
    budget_terms = (
        "budget",
        "cost",
        "how much",
        "money",
        "afford",
        "expensive",
    )
    return any(term in normalized for term in travel_terms) and any(
        term in normalized for term in budget_terms
    )


def question_message(step: int) -> AIMessage:
    question = TRIP_BUDGET_QUESTIONS[step]
    return AIMessage(
        content=question["prompt"],
        additional_kwargs={
            "tripweaver_quick_replies": {
                "question_id": question["id"],
                "step": step + 1,
                "total_steps": len(TRIP_BUDGET_QUESTIONS),
                "allow_custom_answer": True,
                "options": [
                    {
                        "id": f"{question['id']}-{index}",
                        "label": label,
                        "value": value,
                    }
                    for index, (label, value) in enumerate(
                        question["options"], start=1
                    )
                ],
            }
        },
    )


def start_trip_budget_intake(original_request: str) -> GuidedIntake:
    return {
        "kind": "trip_budget",
        "status": "collecting",
        "step": 0,
        "original_request": original_request,
        "answers": {},
    }


def record_trip_budget_answer(
    intake: GuidedIntake, answer: str
) -> tuple[GuidedIntake, AIMessage | None]:
    current_step = intake["step"]
    answers = dict(intake["answers"])
    answers[TRIP_BUDGET_QUESTIONS[current_step]["answer_key"]] = answer
    next_step = current_step + 1
    completed = next_step >= len(TRIP_BUDGET_QUESTIONS)
    updated: GuidedIntake = {
        **intake,
        "status": "completed" if completed else "collecting",
        "step": next_step,
        "answers": answers,
    }
    return updated, None if completed else question_message(next_step)
