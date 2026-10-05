"""Upload generated images to S3-compatible object storage.

The official Instagram API fetches media from a public URL, so images are
stored here and the returned URL is handed to Meta when creating a container.
Works with AWS S3, MinIO, Cloudflare R2, Backblaze B2, etc.
"""

from __future__ import annotations

from dataclasses import dataclass

import boto3
from botocore.client import BaseClient
from botocore.config import Config

from ..config import S3Settings


@dataclass(frozen=True)
class S3Uploader:
    """Stores image bytes and returns publicly fetchable URLs."""

    client: BaseClient
    bucket: str
    prefix: str
    endpoint_url: str

    @classmethod
    def from_settings(cls, settings: S3Settings) -> S3Uploader:
        # Path-style addressing (`host/bucket/key`) is required for custom
        # S3-compatible endpoints like MinIO; SigV4 for those endpoints too.
        client = boto3.client(
            "s3",
            endpoint_url=settings.endpoint_url,
            region_name=settings.region,
            aws_access_key_id=settings.access_key,
            aws_secret_access_key=settings.secret_key,
            config=Config(s3={"addressing_style": "path"}, signature_version="s3v4"),
        )
        return cls(
            client=client,
            bucket=settings.bucket,
            prefix=settings.prefix.strip("/"),
            endpoint_url=settings.endpoint_url.rstrip("/"),
        )

    def build_key(self, post_id: str, filename: str) -> str:
        parts = [part for part in (self.prefix, post_id, filename) if part]
        return "/".join(parts)

    def upload(self, key: str, data: bytes, content_type: str = "image/jpeg") -> str:
        """Store ``data`` under ``key`` and return the URL Meta should fetch."""
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return f"{self.endpoint_url}/{self.bucket}/{key}"
