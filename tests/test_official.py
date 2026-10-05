import io
from pathlib import Path
from typing import Any, cast

import pytest
from PIL import Image

from instagram_pipeline.config import InstagramSettings
from instagram_pipeline.uploader.official import OfficialPublisher, to_jpeg


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class _FakeHttp:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []
        self._containers = iter(["child-1", "child-2"])

    def post(self, url: str, data: dict[str, Any] | None = None) -> _FakeResponse:
        self.calls.append(("POST", url, data))
        if url.endswith("/media_publish"):
            return _FakeResponse({"id": "media-1"})
        if data and data.get("media_type") == "CAROUSEL":
            return _FakeResponse({"id": "parent-1"})
        return _FakeResponse({"id": next(self._containers)})

    def get(self, url: str, params: dict[str, Any] | None = None) -> _FakeResponse:
        self.calls.append(("GET", url, params))
        if params and params.get("fields") == "permalink":
            return _FakeResponse({"permalink": "https://instagram.com/p/abc/"})
        return _FakeResponse({"status_code": "FINISHED"})


def _publisher(client: _FakeHttp) -> OfficialPublisher:
    settings = InstagramSettings(
        access_token="token",
        ig_user_id="17841400000000000",
    )
    base = OfficialPublisher.from_settings(settings)
    return OfficialPublisher(
        client=cast(Any, client),
        ig_user_id=base.ig_user_id,
        access_token=base.access_token,
        api_version=base.api_version,
    )


def _posts(client: _FakeHttp) -> list[dict[str, Any]]:
    return [
        data
        for kind, url, data in client.calls
        if kind == "POST" and url.endswith("/media") and data is not None
    ]


def test_to_jpeg_converts_png_to_jpeg(tmp_path: Path) -> None:
    source = tmp_path / "card.png"
    Image.new("RGBA", (16, 16), (10, 20, 30, 255)).save(source, format="PNG")

    data = to_jpeg(source)

    assert data[:2] == b"\xff\xd8"
    assert Image.open(io.BytesIO(data)).format == "JPEG"


def test_publish_single_image_creates_and_publishes_container() -> None:
    client = _FakeHttp()
    result = _publisher(client).publish(["https://cdn.example.com/a.jpg"], "hello")

    assert result.media_id == "media-1"
    assert result.permalink == "https://instagram.com/p/abc/"
    media_posts = _posts(client)
    assert len(media_posts) == 1
    assert media_posts[0]["image_url"] == "https://cdn.example.com/a.jpg"
    assert media_posts[0]["caption"] == "hello"
    publishes = [d for k, u, d in client.calls if u.endswith("/media_publish")]
    assert publishes == [{"creation_id": "child-1", "access_token": "token"}]


def test_publish_carousel_creates_children_then_parent() -> None:
    client = _FakeHttp()
    result = _publisher(client).publish(
        ["https://cdn.example.com/a.jpg", "https://cdn.example.com/b.jpg"],
        "trip",
    )

    assert result.media_id == "media-1"
    media_posts = _posts(client)
    assert len(media_posts) == 3
    assert media_posts[0]["is_carousel_item"] == "true"
    assert media_posts[1]["is_carousel_item"] == "true"
    parent = media_posts[2]
    assert parent["media_type"] == "CAROUSEL"
    assert parent["children"] == "child-1,child-2"
    assert parent["caption"] == "trip"
    publishes = [d for k, u, d in client.calls if u.endswith("/media_publish")]
    assert publishes == [{"creation_id": "parent-1", "access_token": "token"}]


def test_publish_requires_at_least_one_url() -> None:
    client = _FakeHttp()
    with pytest.raises(ValueError):
        _publisher(client).publish([], "empty")
