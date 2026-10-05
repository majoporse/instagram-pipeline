"""POST /auth/logout — clear the session cookie."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from ....config import AuthSettings
from ...auth import get_auth_settings
from ...models import LogoutResponse

router = APIRouter()


@router.post(
    "/auth/logout",
    response_model=LogoutResponse,
    tags=["auth"],
    summary="Log out and clear the session cookie",
    description="Clears the authentication cookie so the browser session ends.",
)
def logout(
    response: Response,
    settings: Annotated[AuthSettings, Depends(get_auth_settings)],
) -> LogoutResponse:
    response.delete_cookie(
        key=settings.cookie_name,
        path="/",
        domain=settings.cookie_domain,
    )
    return LogoutResponse(status="ok")
