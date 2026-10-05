"""Configuration loading with strict typing.

Secrets live in `config.yaml` (gitignored). See `config.yaml.example`.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

ROOT_DIR = Path(__file__).resolve().parents[2]
PACKAGE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = ROOT_DIR / "config.yaml"
TEMPLATES_DIR = PACKAGE_DIR / "renderer" / "templates"

# Keyless map tile styles (see config.yaml.example for alternatives).
DEFAULT_MAP_TILES = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"


def _resolve(path: Path) -> Path:
    return path.expanduser().resolve()


class OpenAISettings(BaseModel):
    api_key: str
    base_url: str | None = None
    model: str = "gpt-4o-mini"


class InstagramSettings(BaseModel):
    """Meta's official API: Instagram API with Instagram Login.

    Publishing runs through a Professional account with a long-lived access
    token; media is served to Meta from public URLs (see `S3Settings`).
    """

    # Long-lived Instagram user access token (~60 days, refreshable).
    access_token: str
    # Instagram professional account id (graph.instagram.com /me -> user_id).
    ig_user_id: str
    graph_api_version: str = "v23.0"


class S3Settings(BaseModel):
    """S3-compatible object storage hosting images for the official API.

    The URL Meta fetches is built in bucket (path) form from this endpoint:
    ``{endpoint_url}/{bucket}/{key}``. So `endpoint_url` must be reachable by
    Meta (e.g. ``https://s3.pipeline.hatal.cc``).
    """

    endpoint_url: str
    region: str = "us-east-1"
    access_key: str
    secret_key: str
    bucket: str
    # Key prefix inside the bucket (keeps posts namespaced).
    prefix: str = "posts"


class AuthSettings(BaseModel):
    """Single hardcoded API login plus JWT/cookie settings.

    The API is exposed publicly, so `secret_key` must be a long random value
    kept secret in `config.yaml`; changing it invalidates existing sessions.
    """

    username: str = "admin"
    password: str = Field(min_length=8)
    secret_key: str = Field(min_length=32)
    algorithm: str = "HS256"
    token_expire_minutes: int = 60 * 24 * 30
    cookie_name: str = "access_token"
    cookie_secure: bool = False
    cookie_domain: str | None = None


class PathSettings(BaseModel):
    """Filesystem paths the pipeline reads from.

    Only the bundled HTML templates are read from disk; source photos and
    generated images are handled in memory and stored in S3.
    """

    templates_dir: Path = TEMPLATES_DIR

    @model_validator(mode="after")
    def resolve_relative_paths(self) -> PathSettings:
        self.templates_dir = _resolve(self.templates_dir)
        return self


class ImageSettings(BaseModel):
    template: str = "composed.html"
    output_size: int = 1080
    border_size: int = 40
    border_color: str = "#808080"
    shadow: bool = True


class RenderSettings(BaseModel):
    template: str = "metadata.html"
    viewport_width: int = 1080
    viewport_height: int = 1080
    map_tiles: str = DEFAULT_MAP_TILES
    map_attribution: str = ""


class CaptionSettings(BaseModel):
    hashtags: list[str] = Field(default_factory=list)


class UploadSettings(BaseModel):
    dry_run: bool = True
    publish_immediately: bool = True
    # True = post composed photo + metadata card as a carousel; False = composed only.
    carousel: bool = True


class Config(BaseModel):
    openai: OpenAISettings
    instagram: InstagramSettings
    auth: AuthSettings
    paths: PathSettings = Field(default_factory=PathSettings)
    image: ImageSettings = Field(default_factory=ImageSettings)
    render: RenderSettings = Field(default_factory=RenderSettings)
    caption: CaptionSettings = Field(default_factory=CaptionSettings)
    upload: UploadSettings = Field(default_factory=UploadSettings)
    # S3-compatible storage hosting the images Meta fetches when publishing.
    s3: S3Settings


# Environment overrides: container deployments keep non-secret settings in a
# ConfigMap and inject secrets as env vars, which the loader overlays here.
_ENV_OVERRIDES: dict[tuple[str, str], str] = {
    ("openai", "api_key"): "OPENAI_API_KEY",
    ("instagram", "access_token"): "INSTAGRAM_ACCESS_TOKEN",
    ("auth", "password"): "AUTH_PASSWORD",
    ("auth", "secret_key"): "AUTH_SECRET_KEY",
    ("s3", "endpoint_url"): "S3_ENDPOINT_URL",
    ("s3", "region"): "S3_REGION",
    ("s3", "access_key"): "S3_ACCESS_KEY",
    ("s3", "secret_key"): "S3_SECRET_KEY",
    ("s3", "bucket"): "S3_BUCKET",
    ("s3", "prefix"): "S3_PREFIX",
}


def _apply_env_overrides(raw: dict[str, object]) -> dict[str, object]:
    for (section, field), env_name in _ENV_OVERRIDES.items():
        value = os.environ.get(env_name)
        if value is None:
            continue
        block = raw.setdefault(section, {})
        if isinstance(block, dict):
            block[field] = value
    return raw


@lru_cache(maxsize=1)
def load_config(path: Path | None = None) -> Config:
    config_file = path or CONFIG_PATH
    if not config_file.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_file}. "
            f"Copy config.yaml.example to config.yaml and fill in your values."
        )
    with config_file.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return Config.model_validate(_apply_env_overrides(raw))
