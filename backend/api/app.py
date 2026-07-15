"""FastAPI app factory."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from config import Settings, settings
from core.security import VALID_API_KEYS


def create_app(app_settings: Settings = settings) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logger = logging.getLogger("tripweaver")

    if not VALID_API_KEYS:
        logger.warning(
            "TRIPWEAVER_API_KEYS is not set - /chat/stream is running WITHOUT auth. "
            "This is fine for local dev only; set it before deploying."
        )

    app = FastAPI(title=app_settings.app_name, version=app_settings.app_version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_methods=["POST", "GET"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )
    app.include_router(router)
    return app
