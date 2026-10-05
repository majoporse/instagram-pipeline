import io
from pathlib import Path
from typing import cast

import pytest
from PIL import Image

from instagram_pipeline.api import service as service_module
from instagram_pipeline.api.service import PipelineService
from instagram_pipeline.config import Config
from instagram_pipeline.uploader.official import PublishedPost
from instagram_pipeline.uploader.storage import S3Uploader


def _official_config(carousel: bool) -> Config:
    return Config.model_validate(
        {
            "openai": {"api_key": "x"},
            "instagram": {"access_token": "tok", "ig_user_id": "123"},
            "auth": {"password": "password1", "secret_key": "x" * 32},
            "s3": {
                "endpoint_url": "https://s3.example.com",
                "access_key": "a",
                "secret_key": "b",
                "bucket": "c",
            },
            "upload": {"carousel": carousel},
        }
    )


def _png_bytes(color: tuple[int, int, int]) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buffer, format="PNG")
    return buffer.getvalue()


class _FakeStorage:
    def __init__(self) -> None:
        self.uploads: list[tuple[str, bytes, str]] = []

    def build_key(self, post_id: str, filename: str) -> str:
        return f"{post_id}/{filename}"

    def upload(self, key: str, data: bytes, content_type: str = "image/jpeg") -> str:
        self.uploads.append((key, data, content_type))
        return f"http://host/c/{key}"


class _FakeOfficial:
    def __init__(self) -> None:
        self.urls: list[str] = []
        self.caption: str = ""

    def publish(self, image_urls: list[str], caption: str) -> PublishedPost:
        self.urls = list(image_urls)
        self.caption = caption
        return PublishedPost(media_id="m1", permalink="https://instagram.com/p/x/")


def _fake_official(monkeypatch: pytest.MonkeyPatch) -> _FakeOfficial:
    official = _FakeOfficial()
    monkeypatch.setattr(
        service_module.OfficialPublisher, "from_settings", staticmethod(lambda settings: official)
    )
    return official


def test_publish_official_uploads_jpegs_then_publishes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    composed = _png_bytes((1, 2, 3))
    card = _png_bytes((4, 5, 6))

    storage = _FakeStorage()
    official = _fake_official(monkeypatch)

    service = PipelineService(config=_official_config(carousel=True))
    result = service._publish_official(
        composed, card, "hi", "post1", cast(S3Uploader, storage)
    )

    assert result.published is True
    assert result.media_id == "m1"
    assert result.permalink == "https://instagram.com/p/x/"
    assert official.caption == "hi"
    assert official.urls == [
        "http://host/c/post1/post1-0.jpg",
        "http://host/c/post1/post1-1.jpg",
    ]
    assert [key for key, _, _ in storage.uploads] == [
        "post1/post1-0.jpg",
        "post1/post1-1.jpg",
    ]
    assert all(content_type == "image/jpeg" for _, _, content_type in storage.uploads)
    assert all(data[:2] == b"\xff\xd8" for _, data, _ in storage.uploads)


def test_publish_official_single_image_when_carousel_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    composed = _png_bytes((1, 2, 3))
    card = _png_bytes((4, 5, 6))

    storage = _FakeStorage()
    official = _fake_official(monkeypatch)

    service = PipelineService(config=_official_config(carousel=False))
    service._publish_official(composed, card, "hi", "post2", cast(S3Uploader, storage))

    assert len(official.urls) == 1
    assert official.urls[0] == "http://host/c/post2/post2-0.jpg"
