"""System routes (public)."""

from __future__ import annotations

from fastapi import APIRouter

from . import health

router = APIRouter()
router.include_router(health.router)

__all__ = ["router"]
