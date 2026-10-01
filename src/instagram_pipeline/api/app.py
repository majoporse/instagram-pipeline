"""FastAPI application factory for the Instagram pipeline.

Interactive docs are served at `/docs` (Swagger UI) and `/redoc`.
"""

from __future__ import annotations

from fastapi import FastAPI

from .routes import API_PREFIX, router

_DESCRIPTION = """
Expose the Instagram posting pipeline over HTTP.

Upload one source photo and the service will:

1. extract EXIF metadata (camera, exposure, GPS),
2. compose the exact 1:1 bordered image,
3. render the 1:1 metadata card,
4. generate a caption (vision LLM) unless one is provided,
5. optionally publish both images to Instagram.

Images are written to `output/api/<post_id>/` and can be downloaded by id.
"""

_TAGS_METADATA = [
    {
        "name": "image-processing",
        "description": "Step 1: compose the exact 1:1 bordered image.",
    },
    {
        "name": "renderer",
        "description": "Step 2: render the EXIF metadata card to PNG.",
    },
    {
        "name": "caption",
        "description": "Step 3: generate a caption with the vision LLM.",
    },
    {
        "name": "posts",
        "description": "Run the full pipeline and download the generated 1:1 images.",
    },
    {
        "name": "system",
        "description": "Service liveness and diagnostics.",
    },
]


def create_app() -> FastAPI:
    """Build the FastAPI application with the pipeline router attached."""
    app = FastAPI(
        title="Instagram Pipeline API",
        version="0.1.0",
        summary="Run the Instagram posting pipeline from an HTTP API.",
        description=_DESCRIPTION,
        openapi_tags=_TAGS_METADATA,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(router, prefix=API_PREFIX)
    return app


app = create_app()
