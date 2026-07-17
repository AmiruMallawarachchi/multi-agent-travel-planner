"""HTTP route handlers for TripWeaver."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from agents.graph import graph
from agents.mcp_client import get_server_statuses
from api.schemas import (
    AuthResponse,
    ChatRequest,
    ConversationSyncRequest,
    ConversationsResponse,
    ExternalAuthRequest,
    HealthResponse,
    LoginRequest,
    PlanSyncRequest,
    PlansResponse,
    RegisterRequest,
    SessionEvent,
    SessionResponse,
    UserResponse,
)
from api.sse import (
    done_event,
    encode_sse,
    stream_events_from_graph_event,
    user_safe_error,
)
from core.security import (
    check_rate_limit,
    client_identity,
    new_session_id,
    require_api_key,
    sanitize_user_message,
    validate_session_id,
)
from core.accounts import (
    AccountError,
    AccountUser,
    authenticate_user,
    authenticate_external_user,
    clear_user_conversations,
    delete_user_conversation,
    delete_user_plan,
    list_user_conversations,
    list_user_plans,
    register_user,
    require_user,
    revoke_token,
    upsert_user_conversation,
    upsert_user_plan,
)
from core.supabase_auth import ExternalAuthError, verify_supabase_google_token

logger = logging.getLogger("tripweaver")
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="tripweaver-backend",
        mcp_servers=await get_server_statuses(),
    )


@router.post("/session", response_model=SessionResponse)
async def create_session(
    request: Request, api_key: str = Depends(require_api_key)
) -> SessionResponse:
    check_rate_limit(client_identity(request, api_key))
    return SessionResponse(session_id=new_session_id())


def _user_response(user: AccountUser) -> UserResponse:
    return UserResponse(**user.public())


@router.post("/auth/register", response_model=AuthResponse)
async def register(
    payload: RegisterRequest, request: Request, api_key: str = Depends(require_api_key)
) -> AuthResponse:
    check_rate_limit(client_identity(request, api_key))
    try:
        token, user = register_user(payload.email, payload.password, payload.name)
    except AccountError as exc:
        raise HTTPException(400, str(exc)) from exc
    return AuthResponse(token=token, user=_user_response(user))


@router.post("/auth/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest, request: Request, api_key: str = Depends(require_api_key)
) -> AuthResponse:
    check_rate_limit(client_identity(request, api_key))
    try:
        authenticated = authenticate_user(payload.email, payload.password)
    except AccountError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not authenticated:
        raise HTTPException(401, "Invalid email or password")
    token, user = authenticated
    return AuthResponse(token=token, user=_user_response(user))


@router.post("/auth/oauth", response_model=AuthResponse)
async def oauth_login(
    payload: ExternalAuthRequest,
    request: Request,
    api_key: str = Depends(require_api_key),
) -> AuthResponse:
    check_rate_limit(client_identity(request, api_key))
    try:
        identity = await verify_supabase_google_token(payload.access_token)
        token, user = authenticate_external_user(
            identity.provider,
            identity.subject,
            identity.email,
            identity.name,
        )
    except ExternalAuthError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    except AccountError as exc:
        raise HTTPException(400, str(exc)) from exc
    return AuthResponse(token=token, user=_user_response(user))


@router.post("/auth/logout")
async def logout(
    authorization: str | None = Header(default=None),
    _: str = Depends(require_api_key),
) -> dict[str, bool]:
    if authorization and authorization.startswith("Bearer "):
        revoke_token(authorization.removeprefix("Bearer ").strip())
    return {"ok": True}


@router.get("/auth/me", response_model=UserResponse)
async def me(user: AccountUser = Depends(require_user)) -> UserResponse:
    return _user_response(user)


@router.get("/conversations", response_model=ConversationsResponse)
async def conversations(user: AccountUser = Depends(require_user)) -> ConversationsResponse:
    return ConversationsResponse(conversations=list_user_conversations(user.id))


@router.put("/conversations/{conversation_id}")
async def save_conversation(
    conversation_id: str,
    payload: ConversationSyncRequest,
    user: AccountUser = Depends(require_user),
) -> dict[str, object]:
    conversation = payload.conversation
    if conversation.get("id") != conversation_id:
        raise HTTPException(422, "Conversation id does not match route")
    try:
        saved = upsert_user_conversation(user.id, conversation)
    except AccountError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"ok": True, "conversation": saved}


@router.delete("/conversations")
async def clear_conversations(user: AccountUser = Depends(require_user)) -> dict[str, bool]:
    clear_user_conversations(user.id)
    return {"ok": True}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: AccountUser = Depends(require_user),
) -> dict[str, bool]:
    try:
        deleted = delete_user_conversation(user.id, conversation_id)
    except AccountError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"ok": True, "deleted": deleted}


@router.get("/plans", response_model=PlansResponse)
async def plans(user: AccountUser = Depends(require_user)) -> PlansResponse:
    return PlansResponse(plans=list_user_plans(user.id))


@router.put("/plans/{plan_id}")
async def save_plan(
    plan_id: str,
    payload: PlanSyncRequest,
    user: AccountUser = Depends(require_user),
) -> dict[str, object]:
    plan = payload.plan
    if plan.get("id") != plan_id:
        raise HTTPException(422, "Plan id does not match route")
    try:
        saved = upsert_user_plan(user.id, plan)
    except AccountError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"ok": True, "plan": saved}


@router.delete("/plans/{plan_id}")
async def delete_plan(
    plan_id: str,
    user: AccountUser = Depends(require_user),
) -> dict[str, bool]:
    try:
        deleted = delete_user_plan(user.id, plan_id)
    except AccountError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"ok": True, "deleted": deleted}


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    request: Request,
    api_key: str = Depends(require_api_key),
):
    identity = client_identity(request, api_key)
    check_rate_limit(identity)

    request_id = uuid.uuid4().hex[:8]
    try:
        message = sanitize_user_message(payload.message)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    session_id = payload.session_id or new_session_id()
    try:
        session_id = validate_session_id(session_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    config = {"configurable": {"thread_id": session_id}}
    inputs = {
        "messages": [{"role": "user", "content": message}],
        "session_id": session_id,
    }

    logger.info(
        "request_id=%s session=%s identity=%s chars=%d",
        request_id,
        session_id,
        identity,
        len(message),
    )
    started = time.monotonic()

    async def event_generator():
        yield encode_sse(SessionEvent(session_id=session_id))
        try:
            async for event in graph.astream_events(
                inputs, config=config, version="v2"
            ):
                for stream_event in stream_events_from_graph_event(event):
                    yield encode_sse(stream_event)

            elapsed_ms = int((time.monotonic() - started) * 1000)
            logger.info(
                "request_id=%s session=%s completed in %dms",
                request_id,
                session_id,
                elapsed_ms,
            )
            yield encode_sse(done_event())

        except Exception:  # noqa: BLE001 - conversation failures become user-safe SSE events
            logger.exception(
                "request_id=%s session=%s chat_stream failed", request_id, session_id
            )
            yield encode_sse(user_safe_error())
            yield encode_sse(done_event())

    return StreamingResponse(event_generator(), media_type="text/event-stream")
