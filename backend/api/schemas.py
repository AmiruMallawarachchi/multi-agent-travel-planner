"""Request/response schemas for the HTTP API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class LivenessResponse(BaseModel):
    status: Literal["ok"]
    service: str


class ToolRuntimeResponse(BaseModel):
    mode: Literal["mcp", "local"]
    transport: Literal["streamable_http", "in_process"]
    configured_servers: int = Field(..., ge=0)


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    mcp_servers: dict[str, Literal["available", "unavailable"]]
    account_storage: dict[str, str] | None = None
    tool_runtime: ToolRuntimeResponse


class SessionResponse(BaseModel):
    session_id: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=8, max_length=256)
    name: str | None = Field(default=None, max_length=80)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=1, max_length=256)


class ExternalAuthRequest(BaseModel):
    access_token: str = Field(..., min_length=16, max_length=8192)


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    created_at: str
    avatar_url: str | None = None


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class ConversationSyncRequest(BaseModel):
    conversation: dict[str, Any]


class ConversationsResponse(BaseModel):
    conversations: list[dict[str, Any]]


class PlanSyncRequest(BaseModel):
    plan: dict[str, Any]


class PlansResponse(BaseModel):
    plans: list[dict[str, Any]]


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


class QuickReplyOption(BaseModel):
    id: str
    label: str
    value: str


class QuickRepliesEvent(BaseModel):
    type: Literal["quick_replies"] = "quick_replies"
    options: list[QuickReplyOption]
    allow_custom_answer: bool = True
    question_id: str | None = None
    step: int | None = Field(default=None, ge=1)
    total_steps: int | None = Field(default=None, ge=1)


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
    | QuickRepliesEvent
    | ErrorEvent
    | DoneEvent
)
