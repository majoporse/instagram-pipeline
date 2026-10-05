"""POST /auth/login — exchange credentials for a JWT session cookie."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from ....config import AuthSettings
from ...auth import create_access_token, get_auth_settings, verify_credentials
from ...models import TokenResponse, User

router = APIRouter()


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    tags=["auth"],
    summary="Log in and receive a session cookie",
    description=(
        "Exchange the configured username/password for a signed JWT. The token is "
        "returned in the body and set as an HttpOnly cookie (`Secure` and `SameSite=Lax`), "
        "so a browser stays logged in until the cookie/token expires."
    ),
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Invalid username or password."},
    },
)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
    settings: Annotated[AuthSettings, Depends(get_auth_settings)],
) -> TokenResponse:
    if not verify_credentials(settings, form.username, form.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token, expires_in = create_access_token(settings, form.username)
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=expires_in,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        domain=settings.cookie_domain,
        path="/",
    )
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=User(username=form.username),
    )
