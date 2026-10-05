"""Authentication routes (one route per file)."""

from __future__ import annotations

from fastapi import APIRouter

from . import login, logout, me

router = APIRouter()
router.include_router(login.router)
router.include_router(logout.router)
router.include_router(me.router)

__all__ = ["router"]
