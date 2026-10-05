"""GET /auth/me — return the authenticated user."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from ...auth import get_current_user
from ...models import User

router = APIRouter()


@router.get(
    "/auth/me",
    response_model=User,
    tags=["auth"],
    summary="Return the current user",
    description="Validates the session cookie (or bearer token) and returns the user.",
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Not authenticated."}},
)
def me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user
