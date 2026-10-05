"""Publish to Instagram through Meta's official Content Publishing API.

Uses the "Instagram API with Instagram Login" host (`graph.instagram.com`).
Publishing is container-based: create a container per image, optionally a
carousel parent, wait for processing, then publish. Meta fetches the media
itself, so each image must be reachable at a public URL.
"""

from __future__ import annotations

import io
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import httpx
from PIL import Image

from ..config import InstagramSettings

GRAPH_BASE = "https://graph.instagram.com"
_FINISHED = "FINISHED"
_ERROR = "ERROR"
_POLL_ATTEMPTS = 30
_POLL_INTERVAL_SECONDS = 2.0


@dataclass(frozen=True)
class PublishedPost:
    """Result of a successful official publish."""

    media_id: str
    permalink: str | None = None


def _error_detail(response: httpx.Response) -> str:
    try:
        error = response.json().get("error") or {}
    except ValueError:
        return response.text[:300]
    parts = [str(error.get("message") or "")]
    for key in ("type", "code", "error_subcode", "error_user_msg", "error_user_title"):
        if error.get(key):
            parts.append(f"{key}={error[key]}")
    return " | ".join(part for part in parts if part) or response.text[:300]


def _raise_for_status(response: httpx.Response) -> None:
    """Like `raise_for_status`, but include Instagram's error body in the message."""
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise httpx.HTTPStatusError(
            f"{exc}. Instagram error: {_error_detail(response)}",
            request=response.request,
            response=response,
        ) from exc


def to_jpeg(image: bytes | Path, quality: int = 92) -> bytes:
    """Convert any Pillow-readable image to JPEG bytes (feed API requires JPEG)."""
    source = io.BytesIO(image) if isinstance(image, (bytes, bytearray)) else image
    with Image.open(source) as img:
        buffer = io.BytesIO()
        img.convert("RGB").save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


@dataclass(frozen=True)
class OfficialPublisher:
    """Wraps the Graph API container flow for photos and carousels."""

    client: httpx.Client
    ig_user_id: str
    access_token: str
    api_version: str

    @classmethod
    def from_settings(cls, settings: InstagramSettings) -> OfficialPublisher:
        if not settings.access_token or not settings.ig_user_id:
            raise ValueError("official mode requires instagram.access_token and ig_user_id")
        return cls(
            client=httpx.Client(timeout=60.0),
            ig_user_id=settings.ig_user_id,
            access_token=settings.access_token,
            api_version=settings.graph_api_version,
        )

    def publish(self, image_urls: Sequence[str], caption: str) -> PublishedPost:
        """Publish one image as a photo, or several as a carousel."""
        if not image_urls:
            raise ValueError("At least one image URL is required.")
        if len(image_urls) == 1:
            container_id = self._create_container(image_urls[0], caption=caption)
        else:
            children = [self._create_container(url, is_carousel_item=True) for url in image_urls]
            container_id = self._create_carousel(children, caption)
        self._wait_until_ready(container_id)
        media_id = self._publish_container(container_id)
        return PublishedPost(media_id=media_id, permalink=self._permalink(media_id))

    # --- internals ---------------------------------------------------------

    def _user_url(self, edge: str) -> str:
        return f"{GRAPH_BASE}/{self.api_version}/{self.ig_user_id}/{edge}"

    def _create_container(
        self,
        image_url: str,
        *,
        caption: str = "",
        is_carousel_item: bool = False,
    ) -> str:
        data: dict[str, str] = {"image_url": image_url, "access_token": self.access_token}
        if is_carousel_item:
            data["is_carousel_item"] = "true"
        if caption:
            data["caption"] = caption
        response = self.client.post(self._user_url("media"), data=data)
        _raise_for_status(response)
        return str(response.json()["id"])

    def _create_carousel(self, children: Sequence[str], caption: str) -> str:
        data = {
            "media_type": "CAROUSEL",
            "children": ",".join(children),
            "caption": caption,
            "access_token": self.access_token,
        }
        response = self.client.post(self._user_url("media"), data=data)
        _raise_for_status(response)
        return str(response.json()["id"])

    def _wait_until_ready(self, container_id: str) -> None:
        url = f"{GRAPH_BASE}/{self.api_version}/{container_id}"
        for _ in range(_POLL_ATTEMPTS):
            response = self.client.get(
                url,
                params={"fields": "status_code", "access_token": self.access_token},
            )
            _raise_for_status(response)
            status = response.json().get("status_code")
            if status == _FINISHED:
                return
            if status == _ERROR:
                raise RuntimeError(f"Instagram container {container_id} failed processing")
            time.sleep(_POLL_INTERVAL_SECONDS)
        raise TimeoutError(
            f"Instagram container {container_id} not ready after {_POLL_ATTEMPTS} polls"
        )

    def _publish_container(self, container_id: str) -> str:
        response = self.client.post(
            self._user_url("media_publish"),
            data={"creation_id": container_id, "access_token": self.access_token},
        )
        _raise_for_status(response)
        return str(response.json()["id"])

    def _permalink(self, media_id: str) -> str | None:
        url = f"{GRAPH_BASE}/{self.api_version}/{media_id}"
        try:
            response = self.client.get(
                url,
                params={"fields": "permalink", "access_token": self.access_token},
            )
            _raise_for_status(response)
        except httpx.HTTPError:
            return None
        permalink = response.json().get("permalink")
        return str(permalink) if permalink else None
