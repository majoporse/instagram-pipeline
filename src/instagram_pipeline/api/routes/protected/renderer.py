"""POST /renderer — Step 2: render the EXIF metadata card."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from ...dependencies import IMAGE_PNG_RESPONSES, get_pipeline_service, read_upload
from ...service import PipelineService

router = APIRouter()


@router.post(
    "/renderer",
    response_class=FileResponse,
    tags=["renderer"],
    summary="Render the metadata card",
    description=(
        "Step 2. Accepts a source photo as `multipart/form-data`, reads its EXIF data "
        "and returns the 1:1 metadata-card PNG. A small map is included when the photo "
        "carries GPS coordinates."
    ),
    responses=IMAGE_PNG_RESPONSES,
)
def render_metadata_card(
    photo: Annotated[
        UploadFile,
        File(description="Source photo (JPEG, PNG or WebP) whose EXIF is rendered."),
    ],
    service: Annotated[PipelineService, Depends(get_pipeline_service)],
) -> FileResponse:
    content = read_upload(photo)
    card = service.render(filename=photo.filename or "upload.jpg", content=content)
    return FileResponse(card, media_type="image/png", filename=card.name)
