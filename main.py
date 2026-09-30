"""Instagram pipeline CLI entrypoint.

Run with: uv run python -m instagram_pipeline.pipeline
"""

from __future__ import annotations

from pathlib import Path

from instagram_pipeline.config import load_config

DEFAULT_PHOTOS_DIR = Path("input/photos")


def main() -> None:
    config = load_config()
    print(f"Loaded config for @{config.instagram.username}")
    print(f"Source photos: {config.paths.source_dir}")
    print(f"Hashtags: {' '.join(config.caption.hashtags)}")


if __name__ == "__main__":
    main()
