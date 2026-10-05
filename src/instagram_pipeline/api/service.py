"""Framework-agnostic services for the pipeline stages.

Each pipeline stage (image processing, renderer, caption) is exposed as its
own method, and `create_post` wires them together for the full pipeline.
Everything returns bytes or strictly typed models and knows nothing about
FastAPI, so the same code can be reused from a CLI or worker.

Nothing is written to the local disk: source photos arrive as bytes, the
generated PNGs are rendered in memory and persisted to S3, and downloads are
streamed back out of S3.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from botocore.exceptions import ClientError

from ..caption.generator import CaptionGenerator, generate_caption
from ..config import Config
from ..image_processing.bordered_image import BorderedImage, compose_photo
from ..image_processing.photo_metadata import PhotoMetadata as ExtractedMetadata
from ..image_processing.photo_metadata import extract_metadata
from ..renderer.renderer import Renderer
from ..uploader import OfficialPublisher, S3Uploader, to_jpeg
from .models import (
    GeneratedImage,
    GpsCoordinates,
    ImageKind,
    PhotoMetadata,
    PostResponse,
    PublishResult,
)

logger = logging.getLogger(__name__)

API_PREFIX = "/api/v1"
_IMAGE_FILENAMES: dict[ImageKind, str] = {
    ImageKind.COMPOSED: "composed.png",
    ImageKind.METADATA_CARD: "metadata-card.png",
}
_MIME_BY_SUFFIX = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
_POST_ID_PATTERN = re.compile(r"[0-9a-f]{32}")


def _mime_for(filename: str) -> str:
    return _MIME_BY_SUFFIX.get(Path(filename).suffix.lower(), "image/jpeg")


@dataclass(frozen=True)
class PipelineService:
    """Runs one pipeline stage, or all of them, for an uploaded photo."""

    config: Config

    # --- individual stages -------------------------------------------------

    def compose(self, *, filename: str, content: bytes) -> bytes:
        """Step 1: compose the exact 1:1 bordered image from the source photo."""
        return self._compose(content, filename)

    def render(self, *, filename: str, content: bytes) -> bytes:
        """Step 2: render the 1:1 metadata card from the source photo's EXIF."""
        return self._render(content)

    def caption(self, *, filename: str, content: bytes) -> str:
        """Step 3: generate an LLM caption from the photo image."""
        return self._caption(content, _mime_for(filename))

    # --- full pipeline -----------------------------------------------------

    def create_post(
        self,
        *,
        filename: str,
        content: bytes,
        caption_override: str | None,
        publish: bool | None,
    ) -> PostResponse:
        post_id = uuid4().hex
        metadata = extract_metadata(content)
        composed = self._compose(content, filename)
        metadata_card = self._render(content)

        storage = S3Uploader.from_settings(self.config.s3)
        self._store_png(storage, post_id, ImageKind.COMPOSED, composed)
        self._store_png(storage, post_id, ImageKind.METADATA_CARD, metadata_card)

        caption = caption_override
        if caption is None:
            caption = self._caption(composed, "image/png")
        publish_result = self._publish(
            composed, metadata_card, caption, publish, post_id, storage
        )

        return PostResponse(
            post_id=post_id,
            caption=caption,
            metadata=_to_metadata(metadata),
            images=[
                self._generated_image(post_id, ImageKind.COMPOSED, self._composed_size()),
                self._generated_image(
                    post_id,
                    ImageKind.METADATA_CARD,
                    (self.config.render.viewport_width, self.config.render.viewport_height),
                ),
            ],
            publish=publish_result,
        )

    def load_image(self, post_id: str, kind: ImageKind) -> bytes | None:
        """Fetch a generated image from S3, guarding against traversal."""
        if _POST_ID_PATTERN.fullmatch(post_id) is None:
            return None
        storage = S3Uploader.from_settings(self.config.s3)
        key = storage.build_key(post_id, _IMAGE_FILENAMES[kind])
        try:
            return storage.download(key)
        except ClientError:
            return None

    # --- internals ---------------------------------------------------------

    def _composed_size(self) -> tuple[int, int]:
        return (self.config.image.output_size, self.config.image.output_size)

    def _compose(self, content: bytes, filename: str) -> bytes:
        result: BorderedImage = compose_photo(
            source=content,
            filename=filename,
            settings=self.config.image,
            templates_dir=self.config.paths.templates_dir,
        )
        return result.data

    def _render(self, content: bytes) -> bytes:
        metadata = extract_metadata(content)
        renderer = Renderer.from_settings(self.config.render, self.config.paths.templates_dir)
        return renderer.render_bytes(metadata.context())

    def _caption(self, image: bytes, mime: str) -> str:
        generator = CaptionGenerator.from_settings(self.config.openai, self.config.caption)
        return generate_caption(image, generator, mime)

    @staticmethod
    def _store_png(storage: S3Uploader, post_id: str, kind: ImageKind, data: bytes) -> None:
        storage.upload(
            storage.build_key(post_id, _IMAGE_FILENAMES[kind]),
            data,
            content_type="image/png",
        )

    def _publish(
        self,
        composed: bytes,
        metadata_card: bytes,
        caption: str,
        publish: bool | None,
        post_id: str,
        storage: S3Uploader,
    ) -> PublishResult:
        should_publish = publish if publish is not None else not self.config.upload.dry_run
        if not should_publish:
            return PublishResult(published=False)
        try:
            return self._publish_official(composed, metadata_card, caption, post_id, storage)
        except Exception as exc:
            logger.exception("Publishing post %s failed", post_id)
            return PublishResult(published=False, error=str(exc))

    def _publish_official(
        self,
        composed: bytes,
        metadata_card: bytes,
        caption: str,
        post_id: str,
        storage: S3Uploader,
    ) -> PublishResult:
        sources = [composed, metadata_card] if self.config.upload.carousel else [composed]
        urls = [
            storage.upload(
                storage.build_key(post_id, f"{post_id}-{index}.jpg"),
                to_jpeg(source),
                content_type="image/jpeg",
            )
            for index, source in enumerate(sources)
        ]
        published = OfficialPublisher.from_settings(self.config.instagram).publish(urls, caption)
        return PublishResult(
            published=True,
            media_id=published.media_id,
            permalink=published.permalink,
        )

    @staticmethod
    def _generated_image(
        post_id: str,
        kind: ImageKind,
        size: tuple[int, int],
    ) -> GeneratedImage:
        width, height = size
        return GeneratedImage(
            kind=kind,
            url=f"{API_PREFIX}/posts/{post_id}/images/{kind.value}",
            width=width,
            height=height,
        )


def _to_metadata(metadata: ExtractedMetadata) -> PhotoMetadata:
    gps = None
    location = None
    if metadata.gps is not None:
        gps = GpsCoordinates(
            latitude=metadata.gps.latitude,
            longitude=metadata.gps.longitude,
        )
        location = f"{metadata.gps.latitude:.4f}, {metadata.gps.longitude:.4f}"
    return PhotoMetadata(
        camera=metadata.camera,
        iso=metadata.iso,
        shutter=metadata.shutter,
        aperture=metadata.aperture,
        date=metadata.date,
        location=location,
        gps=gps,
    )
