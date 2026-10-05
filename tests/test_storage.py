import pytest

from instagram_pipeline.config import S3Settings
from instagram_pipeline.uploader import storage as storage_module
from instagram_pipeline.uploader.storage import S3Uploader


class _FakeS3:
    def __init__(self) -> None:
        self.puts: list[dict[str, object]] = []

    def put_object(self, **kwargs: object) -> None:
        self.puts.append(kwargs)


def _settings(**overrides: object) -> S3Settings:
    values: dict[str, object] = {
        "endpoint_url": "https://s3.example.com",
        "access_key": "access",
        "secret_key": "secret",
        "bucket": "instagram-pipeline",
        "prefix": "posts",
    }
    values.update(overrides)
    return S3Settings.model_validate(values)


def test_upload_puts_object_and_builds_public_url(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeS3()
    monkeypatch.setattr(storage_module.boto3, "client", lambda *args, **kwargs: fake)
    uploader = S3Uploader.from_settings(_settings())

    key = uploader.build_key("abc123", "abc123-0.jpg")
    assert key == "posts/abc123/abc123-0.jpg"

    url = uploader.upload(key, b"jpeg-bytes")

    assert url == "https://s3.example.com/instagram-pipeline/posts/abc123/abc123-0.jpg"
    assert fake.puts == [
        {
            "Bucket": "instagram-pipeline",
            "Key": "posts/abc123/abc123-0.jpg",
            "Body": b"jpeg-bytes",
            "ContentType": "image/jpeg",
        }
    ]


def test_build_key_without_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(storage_module.boto3, "client", lambda *args, **kwargs: _FakeS3())
    uploader = S3Uploader.from_settings(_settings(prefix=""))
    assert uploader.build_key("post", "post-0.jpg") == "post/post-0.jpg"
