"""POST /posts — run the full pipeline for one photo."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from ...dependencies import get_pipeline_service, read_upload
from ...models import ErrorResponse, PostResponse
from ...service import PipelineService

router = APIRouter()


@router.post(
    "/posts",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["posts"],
    summary="Upload a photo and run the full pipeline",
    description=(
        "Runs every step in order: image processing, renderer, caption, and (optionally) "
        "the Instagram upload.\n\n"
        "When `caption` is omitted the caption is generated with the configured vision "
        "LLM from the composed image. When `publish` is omitted it defaults to the inverse "
        "of `upload.dry_run` in `config.yaml`, so the API never posts unless explicitly asked."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Empty upload."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "A pipeline step failed.",
        },
    },
)
def create_post(
    photo: Annotated[
        UploadFile,
        File(description="Source photo (JPEG, PNG or WebP) to process."),
    ],
    service: Annotated[PipelineService, Depends(get_pipeline_service)],
    caption: Annotated[
        str | None,
        Form(description="Override the LLM caption. Generated when omitted."),
    ] = None,
    publish: Annotated[
        bool | None,
        Form(description="Send the post to Instagram. Defaults to `not upload.dry_run`."),
    ] = None,
) -> PostResponse:
    content = read_upload(photo)
    return service.create_post(
        filename=photo.filename or "upload.jpg",
        content=content,
        caption_override=caption,
        publish=publish,
    )
