"""Protected pipeline routes (one route per file).

Authentication is applied **once** here via a router-level dependency, so no
individual handler needs to declare an (unused) user parameter.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...auth import get_current_user
from . import caption, image_download, image_processing, posts, renderer

router = APIRouter(dependencies=[Depends(get_current_user)])
router.include_router(image_processing.router)
router.include_router(renderer.router)
router.include_router(caption.router)
router.include_router(posts.router)
router.include_router(image_download.router)

__all__ = ["router"]
