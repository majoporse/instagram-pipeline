from pathlib import Path

import pytest
from PIL import Image

from instagram_pipeline.api import service as service_module
from instagram_pipeline.api.service import PipelineService
from instagram_pipeline.config import Config
from instagram_pipeline.uploader.official import PublishedPost


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


class _FakeStorage:
    def __init__(self) -> None:
        self.uploads: list[tuple[str, bytes]] = []

    def build_key(self, post_id: str, filename: str) -> str:
        return f"{post_id}/{filename}"

    def upload(self, key: str, data: bytes, content_type: str = "image/jpeg") -> str:
        self.uploads.append((key, data))
        return f"http://host/c/{key}"


class _FakeOfficial:
    def __init__(self) -> None:
        self.urls: list[str] = []
        self.caption: str = ""

    def publish(self, image_urls: list[str], caption: str) -> PublishedPost:
        self.urls = list(image_urls)
        self.caption = caption
        return PublishedPost(media_id="m1", permalink="https://instagram.com/p/x/")


def test_publish_official_uploads_jpegs_then_publishes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    composed = tmp_path / "composed.png"
    card = tmp_path / "card.png"
    Image.new("RGB", (8, 8), (1, 2, 3)).save(composed)
    Image.new("RGB", (8, 8), (4, 5, 6)).save(card)

    storage = _FakeStorage()
    official = _FakeOfficial()
    monkeypatch.setattr(
        service_module.S3Uploader, "from_settings", staticmethod(lambda settings: storage)
    )
    monkeypatch.setattr(
        service_module.OfficialPublisher, "from_settings", staticmethod(lambda settings: official)
    )

    service = PipelineService(config=_official_config(carousel=True), output_root=tmp_path)
    result = service._publish_official(composed, card, "hi", "post1")

    assert result.published is True
    assert result.media_id == "m1"
    assert result.permalink == "https://instagram.com/p/x/"
    assert official.caption == "hi"
    assert official.urls == [
        "http://host/c/post1/post1-0.jpg",
        "http://host/c/post1/post1-1.jpg",
    ]
    assert [key for key, _ in storage.uploads] == [
        "post1/post1-0.jpg",
        "post1/post1-1.jpg",
    ]
    assert all(data[:2] == b"\xff\xd8" for _, data in storage.uploads)


def test_publish_official_single_image_when_carousel_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    composed = tmp_path / "composed.png"
    card = tmp_path / "card.png"
    Image.new("RGB", (8, 8), (1, 2, 3)).save(composed)
    Image.new("RGB", (8, 8), (4, 5, 6)).save(card)

    storage = _FakeStorage()
    official = _FakeOfficial()
    monkeypatch.setattr(
        service_module.S3Uploader, "from_settings", staticmethod(lambda settings: storage)
    )
    monkeypatch.setattr(
        service_module.OfficialPublisher, "from_settings", staticmethod(lambda settings: official)
    )

    service = PipelineService(config=_official_config(carousel=False), output_root=tmp_path)
    service._publish_official(composed, card, "hi", "post2")

    assert len(official.urls) == 1
    assert official.urls[0] == "http://host/c/post2/post2-0.jpg"
