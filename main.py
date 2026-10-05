"""Instagram pipeline CLI entrypoint.

Run with: uv run python -m instagram_pipeline.pipeline
"""

from __future__ import annotations

from instagram_pipeline.config import load_config


def main() -> None:
    config = load_config()
    print(f"Loaded config for IG user {config.instagram.ig_user_id}")
    print(f"Images stored in S3 bucket: {config.s3.bucket}")
    print(f"Hashtags: {' '.join(config.caption.hashtags)}")


if __name__ == "__main__":
    main()
