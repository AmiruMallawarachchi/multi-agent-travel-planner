"""Request/response schemas for the HTTP API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    mcp_servers: dict[str, Literal["available", "unavailable"]]


class SessionResponse(BaseModel):
    session_id: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None


class SessionEvent(BaseModel):
    type: Literal["session"] = "session"
    session_id: str


class StatusEvent(BaseModel):
    type: Literal["status"] = "status"
    state: str
    node: str


class ToolEvent(BaseModel):
    type: Literal["tool"] = "tool"
    status: Literal["INVOKED", "SUCCEEDED", "FAILED"]
    tool: str


class ResultEvent(BaseModel):
    type: Literal["result"] = "result"
    result_type: Literal[
        "flight", "hotel", "itinerary", "weather", "currency", "location"
    ]
    tool: str
    data: Any


class TokenEvent(BaseModel):
    type: Literal["token"] = "token"
    content: str


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"


StreamEvent = (
    SessionEvent
    | StatusEvent
    | ToolEvent
    | ResultEvent
    | TokenEvent
    | ErrorEvent
    | DoneEvent
)
