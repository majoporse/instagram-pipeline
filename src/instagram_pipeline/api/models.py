"""Strictly typed request/response schemas for the pipeline API.

These pydantic models are the single source of truth for the endpoint
signatures and for the generated OpenAPI/Swagger documentation.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class ImageKind(StrEnum):
    """Kinds of generated 1:1 images exposed for download."""

    COMPOSED = "composed"
    METADATA_CARD = "metadata-card"


class GpsCoordinates(BaseModel):
    """WGS84 coordinates extracted from the photo EXIF data."""

    latitude: float = Field(description="Latitude in decimal degrees.")
    longitude: float = Field(description="Longitude in decimal degrees.")


class PhotoMetadata(BaseModel):
    """Camera/exposure/location details read from the photo EXIF block."""

    camera: str | None = Field(default=None, description="Camera make and model.")
    iso: str | None = Field(default=None, description="ISO sensitivity.")
    shutter: str | None = Field(default=None, description="Exposure time, e.g. '1/200s'.")
    aperture: str | None = Field(default=None, description="Aperture, e.g. 'f/2.8'.")
    date: str | None = Field(default=None, description="Original capture datetime.")
    location: str | None = Field(default=None, description="Human-readable 'lat, lng' string.")
    gps: GpsCoordinates | None = Field(
        default=None,
        description="GPS coordinates, present only when the photo carries them.",
    )


class GeneratedImage(BaseModel):
    """A single generated image and where to download it."""

    kind: ImageKind = Field(description="Image role in the post.")
    url: str = Field(description="Relative URL to download the PNG.")
    width: int = Field(description="Image width in pixels.")
    height: int = Field(description="Image height in pixels.")


class PublishResult(BaseModel):
    """Outcome of the Instagram upload step."""

    published: bool = Field(description="True when the post was sent to Instagram.")
    media_id: str | None = Field(default=None, description="Instagram media primary key.")
    permalink: str | None = Field(default=None, description="Public Instagram permalink.")
    error: str | None = Field(
        default=None,
        description="Set when publishing was attempted but failed.",
    )


class CaptionResponse(BaseModel):
    """Caption produced by the standalone caption stage."""

    caption: str = Field(description="Caption body plus the configured hashtags.")


class PostResponse(BaseModel):
    """Everything produced by processing one uploaded photo."""

    post_id: str = Field(description="Opaque id for this processing run.")
    caption: str = Field(description="Caption body plus the configured hashtags.")
    metadata: PhotoMetadata = Field(description="EXIF metadata extracted from the photo.")
    images: list[GeneratedImage] = Field(description="Generated 1:1 images.")
    publish: PublishResult = Field(description="Instagram upload outcome.")


class ErrorResponse(BaseModel):
    """Machine-readable error payload used by the documented error responses."""

    detail: str = Field(description="Human-readable description of the failure.")


class HealthResponse(BaseModel):
    """Liveness payload returned by the health endpoint."""

    status: Literal["ok"] = Field(description="Fixed 'ok' when the service is up.")


class User(BaseModel):
    """Authenticated API user."""

    username: str = Field(description="Username from the configured API login.")


class TokenResponse(BaseModel):
    """JWT issued by the login endpoint (also stored in an HttpOnly cookie)."""

    access_token: str = Field(description="Signed JWT access token.")
    token_type: Literal["bearer"] = Field(default="bearer", description="Token scheme.")
    expires_in: int = Field(description="Token lifetime in seconds.")
    user: User = Field(description="Authenticated user.")


class LogoutResponse(BaseModel):
    """Confirmation that the session cookie was cleared."""

    status: Literal["ok"] = Field(default="ok", description="Fixed 'ok' on success.")
