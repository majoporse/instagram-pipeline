from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from instagram_pipeline.config import (
    ROOT_DIR,
    Config,
    load_config,
)


def _raw(**instagram: object) -> dict[str, object]:
    return {
        "openai": {"api_key": "x"},
        "instagram": instagram,
        "auth": {"password": "password1", "secret_key": "x" * 32},
        "s3": {
            "endpoint_url": "https://s3.example.com",
            "access_key": "a",
            "secret_key": "b",
            "bucket": "c",
        },
    }


def test_load_config_from_example() -> None:
    example = ROOT_DIR / "config.yaml.example"
    assert example.exists()
    config = load_config(example)
    assert isinstance(config, Config)
    assert config.instagram.ig_user_id
    assert config.openai.model == "gpt-4o-mini"


def test_load_config_caches() -> None:
    example = ROOT_DIR / "config.yaml.example"
    assert load_config(example) is load_config(example)


def test_default_paths_point_into_repo() -> None:
    example = ROOT_DIR / "config.yaml.example"
    config = load_config(example)
    assert config.paths.templates_dir.is_absolute()
    assert config.paths.templates_dir.name == "templates"


def test_instagram_credentials_are_required() -> None:
    with pytest.raises(ValidationError):
        Config.model_validate(_raw())


def test_s3_section_is_required() -> None:
    raw = _raw(access_token="token", ig_user_id="123")
    del raw["s3"]
    with pytest.raises(ValidationError):
        Config.model_validate(raw)


def test_official_config_is_valid() -> None:
    config = Config.model_validate(_raw(access_token="token", ig_user_id="123"))

    assert config.instagram.ig_user_id == "123"
    assert config.s3.bucket == "c"


def test_env_overrides_secret_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.safe_dump(_raw(access_token="inline-token", ig_user_id="123")))
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai")
    monkeypatch.setenv("AUTH_PASSWORD", "env-password")
    monkeypatch.setenv("S3_ACCESS_KEY", "env-s3-key")

    config = load_config(config_file)

    assert config.openai.api_key == "env-openai"
    assert config.auth.password == "env-password"
    assert config.s3.access_key == "env-s3-key"
    assert config.instagram.access_token == "inline-token"  # not overridden
