from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from instagram_pipeline.api.app import create_app
from instagram_pipeline.api.models import (
    GeneratedImage,
    ImageKind,
    PhotoMetadata,
    PostResponse,
    PublishResult,
)
from instagram_pipeline.api.routes import get_pipeline_service
from instagram_pipeline.image_processing.bordered_image import BorderedImage

_POST_ID = "0" * 32


class _FakeService:
    def __init__(self, image: Path | None = None) -> None:
        self.image = image
        self.calls: list[str] = []
        self.last: dict[str, Any] = {}

    def compose(self, *, filename: str, content: bytes) -> BorderedImage:
        self.calls.append("compose")
        self.last = {"filename": filename, "content": content}
        assert self.image is not None
        return BorderedImage(path=self.image, size=(1080, 1080))

    def render(self, *, filename: str, content: bytes) -> Path:
        self.calls.append("render")
        self.last = {"filename": filename, "content": content}
        assert self.image is not None
        return self.image

    def caption(self, *, filename: str, content: bytes) -> str:
        self.calls.append("caption")
        self.last = {"filename": filename, "content": content}
        return "generated caption #photography"

    def create_post(
        self,
        *,
        filename: str,
        content: bytes,
        caption_override: str | None,
        publish: bool | None,
    ) -> PostResponse:
        self.calls.append("create_post")
        self.last = {
            "filename": filename,
            "content": content,
            "caption_override": caption_override,
            "publish": publish,
        }
        return PostResponse(
            post_id=_POST_ID,
            caption=caption_override or "generated",
            metadata=PhotoMetadata(camera="NIKON D750"),
            images=[
                GeneratedImage(
                    kind=ImageKind.COMPOSED,
                    url=f"/api/v1/posts/{_POST_ID}/images/composed",
                    width=1080,
                    height=1080,
                ),
            ],
            publish=PublishResult(published=bool(publish)),
        )

    def resolve_image(self, post_id: str, kind: ImageKind) -> Path | None:
        return self.image


def _client(fake: _FakeService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_pipeline_service] = lambda: fake
    return TestClient(app)


def test_health_returns_ok() -> None:
    client = _client(_FakeService())
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_documents_each_stage() -> None:
    client = _client(_FakeService())
    schema = client.get("/openapi.json").json()

    assert schema["info"]["title"] == "Instagram Pipeline API"
    paths = schema["paths"]
    for path in ("/api/v1/image-processing", "/api/v1/renderer", "/api/v1/caption"):
        content = paths[path]["post"]["requestBody"]["content"]
        assert "multipart/form-data" in content
    post = paths["/api/v1/posts"]["post"]
    assert "multipart/form-data" in post["requestBody"]["content"]
    assert "201" in post["responses"]


def test_image_processing_returns_composed_png(tmp_path: Path) -> None:
    image = tmp_path / "composed.png"
    image.write_bytes(b"composed-bytes")
    fake = _FakeService(image=image)
    client = _client(fake)

    response = client.post(
        "/api/v1/image-processing",
        files={"photo": ("source.jpg", b"jpeg-bytes", "image/jpeg")},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"composed-bytes"
    assert fake.calls == ["compose"]


def test_renderer_returns_metadata_card_png(tmp_path: Path) -> None:
    card = tmp_path / "metadata-card.png"
    card.write_bytes(b"card-bytes")
    fake = _FakeService(image=card)
    client = _client(fake)

    response = client.post(
        "/api/v1/renderer",
        files={"photo": ("source.jpg", b"jpeg-bytes", "image/jpeg")},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"card-bytes"
    assert fake.calls == ["render"]


def test_caption_returns_generated_text() -> None:
    fake = _FakeService()
    client = _client(fake)

    response = client.post(
        "/api/v1/caption",
        files={"photo": ("source.jpg", b"jpeg-bytes", "image/jpeg")},
    )

    assert response.status_code == 200
    assert response.json() == {"caption": "generated caption #photography"}
    assert fake.calls == ["caption"]


def test_stage_endpoints_reject_empty_upload() -> None:
    client = _client(_FakeService())
    for path in ("/api/v1/image-processing", "/api/v1/renderer", "/api/v1/caption"):
        response = client.post(path, files={"photo": ("source.jpg", b"", "image/jpeg")})
        assert response.status_code == 400


def test_upload_runs_full_pipeline_with_form_fields() -> None:
    fake = _FakeService()
    client = _client(fake)

    response = client.post(
        "/api/v1/posts",
        files={"photo": ("source.jpg", b"jpeg-bytes", "image/jpeg")},
        data={"caption": "my caption", "publish": "false"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["post_id"] == _POST_ID
    assert body["caption"] == "my caption"
    assert body["publish"] == {
        "published": False,
        "media_id": None,
        "permalink": None,
        "error": None,
    }
    assert fake.last["filename"] == "source.jpg"
    assert fake.last["content"] == b"jpeg-bytes"
    assert fake.last["caption_override"] == "my caption"
    assert fake.last["publish"] is False


def test_upload_requires_a_file() -> None:
    client = _client(_FakeService())
    response = client.post("/api/v1/posts", data={"caption": "x"})
    assert response.status_code == 422


def test_download_generated_image(tmp_path: Path) -> None:
    image = tmp_path / "composed.png"
    image.write_bytes(b"png-bytes")
    client = _client(_FakeService(image=image))

    response = client.get(f"/api/v1/posts/{_POST_ID}/images/composed")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"png-bytes"


def test_download_missing_image_returns_404() -> None:
    client = _client(_FakeService())
    response = client.get(f"/api/v1/posts/{_POST_ID}/images/composed")
    assert response.status_code == 404
