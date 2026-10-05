"""Compose a source photo into an exact 1:1 bordered image.

The layout is delegated to an HTML template (`composed.html`) rendered with
Playwright: `object-fit: contain` keeps the photo unscaled-or-stretched while
centering it inside a bordered frame.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from ..config import ImageSettings, PathSettings
from ..renderer.renderer import Renderer

_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


@dataclass(frozen=True)
class BorderedImage:
    """Result of the 1:1 composition step."""

    path: Path
    size: tuple[int, int]


def compose_photo(
    source: Path,
    output: Path,
    settings: ImageSettings,
    paths: PathSettings,
) -> BorderedImage:
    renderer = Renderer(
        template=settings.template,
        templates_dir=paths.templates_dir,
        width=settings.output_size,
        height=settings.output_size,
    )
    with Image.open(source) as img:
        photo_size = img.size
    _ = renderer.render(
        context={
            "width": settings.output_size,
            "height": settings.output_size,
            "border_size": settings.border_size,
            "border_color": settings.border_color,
            "shadow": settings.shadow,
            "photo_width": photo_size[0],
            "photo_height": photo_size[1],
            "image_src": _image_data_url(source),
        },
        output=output,
    )
    return BorderedImage(path=output, size=(settings.output_size, settings.output_size))


def _image_data_url(image: Path) -> str:
    mime = _MIME.get(image.suffix.lower(), "image/jpeg")
    encoded = base64.b64encode(image.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


if __name__ == "__main__":
    from ..config import load_config

    settings = load_config()
    # settings = config.image.model_copy(update={"output_size": 600, "border_size": 20})

    sample_dir = Path("input/test")
    out_dir = Path("output/manual")
    out_dir.mkdir(parents=True, exist_ok=True)

    result = compose_photo(
        source=sample_dir / "tmel.jpg",
        output=out_dir / "bordered.png",
        settings=settings.image,
        paths=settings.paths,
    )
    print(f"Composed 1:1 image -> {result.path} ({result.size[0]}x{result.size[1]})")
