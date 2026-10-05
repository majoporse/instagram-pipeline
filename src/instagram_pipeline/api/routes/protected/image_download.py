"""GET /posts/{post_id}/images/{kind} — download a generated image."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import FileResponse

from ...dependencies import get_pipeline_service
from ...models import ErrorResponse, ImageKind
from ...service import PipelineService

router = APIRouter()


@router.get(
    "/posts/{post_id}/images/{kind}",
    response_class=FileResponse,
    tags=["posts"],
    summary="Download a generated image",
    description="Fetch one of the 1:1 PNG images produced for a previous upload.",
    responses={
        status.HTTP_200_OK: {
            "content": {"image/png": {}},
            "description": "The requested PNG image.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Unknown post id or image kind.",
        },
    },
)
def get_generated_image(
    post_id: Annotated[
        str,
        Path(description="Post id returned by the upload endpoint."),
    ],
    kind: Annotated[
        ImageKind,
        Path(description="Which generated image to download."),
    ],
    service: Annotated[PipelineService, Depends(get_pipeline_service)],
) -> FileResponse:
    image = service.resolve_image(post_id, kind)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found for this post id.",
        )
    return FileResponse(image, media_type="image/png", filename=image.name)
