"""Run the API with uvicorn: `uv run python -m instagram_pipeline.api`."""

from __future__ import annotations

import uvicorn

from .app import app

HOST = "127.0.0.1"
PORT = 8000


def main() -> None:
    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
