"""GET /health — public liveness probe."""

from __future__ import annotations

from fastapi import APIRouter

from ...models import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
    summary="Service health",
    description="Returns `ok` when the API process is accepting requests.",
)
def health() -> HealthResponse:
    return HealthResponse(status="ok")
