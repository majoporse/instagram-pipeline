from pathlib import Path

from instagram_pipeline.config import InstagramSettings
from instagram_pipeline.uploader.publisher import Publisher, upload_image


class _FakeMedia:
    def __init__(self, pk: str, code: str) -> None:
        self.pk = pk
        self.code = code


class _FakeInstagrapi:
    def __init__(self) -> None:
        self.last_path: str | None = None
        self.last_caption: str | None = None

    def photo_upload(self, path: str, caption: str) -> _FakeMedia:
        self.last_path = path
        self.last_caption = caption
        return _FakeMedia(pk="123", code="abcXYZ")


def _stub_publisher(client: object) -> Publisher:
    settings = InstagramSettings(
        username="user",
        password="pass",
        session_file=Path("output/sessions/session.json"),
    )
    return Publisher(client=client, settings=settings)


def test_upload_image_calls_photo_upload(tmp_path: Path) -> None:
    fake = _FakeInstagrapi()
    publisher = _stub_publisher(fake)
    image = tmp_path / "bordered.jpg"
    image.write_bytes(b"jpeg")

    media = upload_image(image=image, caption="hello", publisher=publisher)

    assert fake.last_path == str(image)
    assert fake.last_caption == "hello"
    assert media.code == "abcXYZ"