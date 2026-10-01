"""Self-contained FastAPI service exposing the Instagram pipeline.

Launch it with:

    uv run python -m instagram_pipeline.api
"""

from __future__ import annotations

from .app import app, create_app

__all__ = ["app", "create_app"]
