"""FastAPI app factory."""
from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agents.mcp_client import using_local_tools, warm_servers
from api.routes import router
from config import Settings, settings
from core.security import VALID_API_KEYS


@contextlib.asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Fire-and-forget: startup must not wait on external services, and a failed
    # warm-up must never stop the backend from serving.
    warm_up = (
        None if using_local_tools() else asyncio.create_task(warm_servers())
    )
    try:
        yield
    finally:
        if warm_up is not None:
            warm_up.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await warm_up


def create_app(app_settings: Settings = settings) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logger = logging.getLogger("tripweaver")

    if not VALID_API_KEYS:
        logger.warning(
            "TRIPWEAVER_API_KEYS is not set - /chat/stream is running WITHOUT auth. "
            "This is fine for local dev only; set it before deploying."
        )

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        lifespan=_lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_methods=["POST", "GET"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )
    app.include_router(router)
    return app
