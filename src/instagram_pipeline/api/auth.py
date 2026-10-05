"""JWT + cookie authentication core for the pipeline API.

A single hardcoded login lives in `config.yaml` (`auth:`). On login the API
issues a signed JWT and stores it in an HttpOnly cookie so browser sessions
persist; API clients may also send it as `Authorization: Bearer <token>`.

The endpoints themselves live under `api.routes.auth`; this module holds the
token helpers and the `get_current_user` dependency used to protect routes.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError

from ..config import AuthSettings, load_config
from .models import User
from .service import API_PREFIX

bearer_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{API_PREFIX}/auth/login",
    auto_error=False,
)


def get_auth_settings() -> AuthSettings:
    """Load the hardcoded login and JWT settings from `config.yaml`."""
    return load_config().auth


def create_access_token(settings: AuthSettings, subject: str) -> tuple[str, int]:
    """Return a signed JWT for `subject` and its lifetime in seconds."""
    now = datetime.now(tz=UTC)
    expires_in = timedelta(minutes=settings.token_expire_minutes)
    payload: dict[str, object] = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_in,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token, int(expires_in.total_seconds())


def decode_access_token(settings: AuthSettings, token: str) -> str | None:
    """Validate a JWT and return its subject, or None when invalid/expired."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
    except InvalidTokenError:
        return None
    subject = payload.get("sub")
    if isinstance(subject, str) and subject:
        return subject
    return None


def get_current_user(
    request: Request,
    settings: Annotated[AuthSettings, Depends(get_auth_settings)],
    bearer_token: Annotated[str | None, Depends(bearer_scheme)],
) -> User:
    """FastAPI dependency: authenticate via cookie or bearer token, else 401.

    Applied once on the protected router, so individual handlers stay clean.
    """
    token = request.cookies.get(settings.cookie_name) or bearer_token
    subject = decode_access_token(settings, token) if token else None
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return User(username=subject)


def verify_credentials(settings: AuthSettings, username: str, password: str) -> bool:
    """Constant-time comparison against the configured credentials."""
    valid_user = secrets.compare_digest(username, settings.username)
    valid_password = secrets.compare_digest(password, settings.password)
    return valid_user and valid_password
