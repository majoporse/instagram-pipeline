"""Aggregate every route module into a single router.

Routes are grouped by exposure:

- `auth/`      — public login/logout plus the authenticated `/auth/me`
- `protected/` — every pipeline stage, guarded once by the router-level
                 `get_current_user` dependency
- `system/`    — public liveness endpoint
"""

from __future__ import annotations

from fastapi import APIRouter

from . import auth, protected, system

router = APIRouter()
router.include_router(auth.router)
router.include_router(protected.router)
router.include_router(system.router)

__all__ = ["router"]
