"""
Typed application settings for the backend.

This module intentionally keeps environment parsing boring and dependency-free:
all deploy-time values are read once through a small immutable object, while
security.py still owns request-time auth/rate-limit behavior.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _csv_env(name: str) -> tuple[str, ...]:
    return tuple(value.strip() for value in os.getenv(name, "").split(",") if value.strip())


@dataclass(frozen=True)
class Settings:
    app_name: str = "TripWeaver API"
    app_version: str = "1.0.0"
    allowed_origins: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(allowed_origins=_csv_env("ALLOWED_ORIGINS"))

    @property
    def cors_origins(self) -> list[str]:
        # Keep local development working out of the box while production
        # deployments are expected to set ALLOWED_ORIGINS explicitly.
        return list(self.allowed_origins or ("http://localhost:7860",))


settings = Settings.from_env()
