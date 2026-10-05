"""POST /image-processing — Step 1: compose the 1:1 bordered image."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from ...dependencies import IMAGE_PNG_RESPONSES, get_pipeline_service, read_upload
from ...service import PipelineService

router = APIRouter()


@router.post(
    "/image-processing",
    response_class=FileResponse,
    tags=["image-processing"],
    summary="Compose the 1:1 bordered image",
    description=(
        "Step 1. Accepts a source photo as `multipart/form-data` and returns the exact "
        "1:1 bordered PNG: the photo is centered on a solid background with a minimum "
        "border, scaled with `object-fit: contain` so it is never cropped or stretched."
    ),
    responses=IMAGE_PNG_RESPONSES,
)
def compose_image(
    photo: Annotated[
        UploadFile,
        File(description="Source photo (JPEG, PNG or WebP) to compose."),
    ],
    service: Annotated[PipelineService, Depends(get_pipeline_service)],
) -> FileResponse:
    content = read_upload(photo)
    result = service.compose(filename=photo.filename or "upload.jpg", content=content)
    return FileResponse(result.path, media_type="image/png", filename=result.path.name)
