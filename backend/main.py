"""ASGI entrypoint for deployment.

The implementation lives in api.app/api.routes so tests can exercise the HTTP
layer without this file becoming a grab-bag of app, route, and SSE concerns.
"""
from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from api.app import create_app

app = create_app()
