"""Shared FastAPI dependencies and route-building helpers."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, UploadFile, status

from ..config import ROOT_DIR, load_config
from .models import ErrorResponse
from .service import PipelineService

EMPTY_UPLOAD_DETAIL = "Upload is empty."

IMAGE_PNG_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_200_OK: {
        "content": {"image/png": {}},
        "description": "The generated 1:1 PNG image.",
    },
    status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Empty upload."},
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "model": ErrorResponse,
        "description": "The stage failed.",
    },
}


def get_pipeline_service() -> PipelineService:
    """Provide the service, loading config lazily so imports stay side-effect free."""
    return PipelineService(config=load_config(), output_root=ROOT_DIR / "output" / "api")


def read_upload(photo: UploadFile) -> bytes:
    """Read the upload synchronously; sync endpoints run in a worker thread.

    Playwright's sync API (used by the composition/render stages) cannot run
    inside the asyncio event loop, so every stage endpoint is a plain `def`.
    """
    content = photo.file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=EMPTY_UPLOAD_DETAIL)
    return content
