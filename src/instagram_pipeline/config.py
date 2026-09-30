"""Configuration loading with strict typing.

Secrets live in `config.yaml` (gitignored). See `config.yaml.example`.
"""

from __future__ import annotations

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
    username: str
    password: str
    session_file: Path = ROOT_DIR / "output" / "sessions" / "session.json"


class PathSettings(BaseModel):
    source_dir: Path = ROOT_DIR / "input" / "photos"
    output_dir: Path = ROOT_DIR / "output" / "images"
    templates_dir: Path = TEMPLATES_DIR

    @model_validator(mode="after")
    def resolve_relative_paths(self) -> PathSettings:
        self.source_dir = _resolve(self.source_dir)
        self.output_dir = _resolve(self.output_dir)
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


class Config(BaseModel):
    openai: OpenAISettings
    instagram: InstagramSettings
    paths: PathSettings = Field(default_factory=PathSettings)
    image: ImageSettings = Field(default_factory=ImageSettings)
    render: RenderSettings = Field(default_factory=RenderSettings)
    caption: CaptionSettings = Field(default_factory=CaptionSettings)
    upload: UploadSettings = Field(default_factory=UploadSettings)


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
    return Config.model_validate(raw)
