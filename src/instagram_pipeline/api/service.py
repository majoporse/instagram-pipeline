"""Framework-agnostic services for the pipeline stages.

Each pipeline stage (image processing, renderer, caption) is exposed as its
own method, and `create_post` wires them together for the full pipeline.
Everything returns paths or strictly typed models and knows nothing about
FastAPI, so the same code can be reused from a CLI or worker.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from ..caption.generator import CaptionGenerator, generate_caption
from ..config import Config
from ..image_processing.bordered_image import BorderedImage, compose_photo
from ..image_processing.photo_metadata import PhotoMetadata as ExtractedMetadata
from ..image_processing.photo_metadata import extract_metadata
from ..renderer.renderer import Renderer, render_template
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
_SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
_POST_ID_PATTERN = re.compile(r"[0-9a-f]{32}")


@dataclass(frozen=True)
class PipelineService:
    """Runs one pipeline stage, or all of them, for an uploaded photo."""

    config: Config
    output_root: Path

    # --- individual stages -------------------------------------------------

    def compose(self, *, filename: str, content: bytes) -> BorderedImage:
        """Step 1: compose the exact 1:1 bordered image from the source photo."""
        work_dir, source = self._stage(filename, content)
        return self._compose(source, work_dir)

    def render(self, *, filename: str, content: bytes) -> Path:
        """Step 2: render the 1:1 metadata card from the source photo's EXIF."""
        work_dir, source = self._stage(filename, content)
        return self._render(source, work_dir)

    def caption(self, *, filename: str, content: bytes) -> str:
        """Step 3: generate an LLM caption from the photo image."""
        _work_dir, source = self._stage(filename, content)
        return self._caption(source)

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
        work_dir = self._work_dir(post_id)
        source = self._save_upload(work_dir, filename, content)

        metadata = extract_metadata(source)
        composed = self._compose(source, work_dir)
        metadata_card = self._render(source, work_dir)

        caption = caption_override if caption_override is not None else self._caption(composed.path)
        publish_result = self._publish(composed.path, metadata_card, caption, publish, post_id)

        return PostResponse(
            post_id=post_id,
            caption=caption,
            metadata=_to_metadata(metadata),
            images=[
                self._generated_image(post_id, ImageKind.COMPOSED, composed.size),
                self._generated_image(
                    post_id,
                    ImageKind.METADATA_CARD,
                    (self.config.render.viewport_width, self.config.render.viewport_height),
                ),
            ],
            publish=publish_result,
        )

    def resolve_image(self, post_id: str, kind: ImageKind) -> Path | None:
        """Return the on-disk path for a generated image, guarding traversal."""
        if _POST_ID_PATTERN.fullmatch(post_id) is None:
            return None
        path = self.output_root / post_id / _IMAGE_FILENAMES[kind]
        if not path.is_file():
            return None
        return path

    # --- internals ---------------------------------------------------------

    def _stage(self, filename: str, content: bytes) -> tuple[Path, Path]:
        work_dir = self._work_dir(uuid4().hex)
        return work_dir, self._save_upload(work_dir, filename, content)

    def _work_dir(self, name: str) -> Path:
        work_dir = self.output_root / name
        work_dir.mkdir(parents=True, exist_ok=True)
        return work_dir

    @staticmethod
    def _save_upload(work_dir: Path, filename: str, content: bytes) -> Path:
        suffix = Path(filename).suffix.lower()
        if suffix not in _SUPPORTED_SUFFIXES:
            suffix = ".jpg"
        source = work_dir / f"source{suffix}"
        source.write_bytes(content)
        return source

    def _compose(self, source: Path, work_dir: Path) -> BorderedImage:
        return compose_photo(
            source=source,
            output=work_dir / _IMAGE_FILENAMES[ImageKind.COMPOSED],
            settings=self.config.image,
            paths=self.config.paths,
        )

    def _render(self, source: Path, work_dir: Path) -> Path:
        metadata = extract_metadata(source)
        renderer = Renderer.from_settings(self.config.render, self.config.paths.templates_dir)
        return render_template(
            context=metadata.context(),
            renderer=renderer,
            output=work_dir / _IMAGE_FILENAMES[ImageKind.METADATA_CARD],
        )

    def _caption(self, image: Path) -> str:
        generator = CaptionGenerator.from_settings(self.config.openai, self.config.caption)
        return generate_caption(image, generator)

    def _publish(
        self,
        composed: Path,
        metadata_card: Path,
        caption: str,
        publish: bool | None,
        post_id: str,
    ) -> PublishResult:
        should_publish = publish if publish is not None else not self.config.upload.dry_run
        if not should_publish:
            return PublishResult(published=False)
        try:
            return self._publish_official(composed, metadata_card, caption, post_id)
        except Exception as exc:
            logger.exception("Publishing post %s failed", post_id)
            return PublishResult(published=False, error=str(exc))

    def _publish_official(
        self,
        composed: Path,
        metadata_card: Path,
        caption: str,
        post_id: str,
    ) -> PublishResult:
        storage = S3Uploader.from_settings(self.config.s3)
        sources = [composed, metadata_card] if self.config.upload.carousel else [composed]
        urls = [
            storage.upload(
                storage.build_key(post_id, f"{post_id}-{index}.jpg"),
                to_jpeg(source),
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
