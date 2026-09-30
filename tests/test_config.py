from instagram_pipeline.config import (
    ROOT_DIR,
    Config,
    load_config,
)


def test_load_config_from_example() -> None:
    example = ROOT_DIR / "config.yaml.example"
    assert example.exists()
    config = load_config(example)
    assert isinstance(config, Config)
    assert config.instagram.username == "your_username"
    assert config.openai.model == "gpt-4o-mini"


def test_load_config_caches() -> None:
    example = ROOT_DIR / "config.yaml.example"
    assert load_config(example) is load_config(example)


def test_default_paths_point_into_repo() -> None:
    example = ROOT_DIR / "config.yaml.example"
    config = load_config(example)
    assert config.paths.templates_dir.is_absolute()
    assert config.paths.templates_dir.name == "templates"
