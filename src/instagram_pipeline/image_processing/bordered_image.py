"""Compose a source photo into an exact 1:1 bordered image.

The layout is delegated to an HTML template (`composed.html`) rendered with
Playwright: `object-fit: contain` keeps the photo unscaled-or-stretched while
centering it inside a bordered frame.

Everything happens in memory: the source comes in as bytes and the composed
PNG is returned as bytes, so no local files are written.
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from ..config import ImageSettings
from ..renderer.renderer import Renderer

_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


@dataclass(frozen=True)
class BorderedImage:
    """Result of the 1:1 composition step."""

    data: bytes
    size: tuple[int, int]


def compose_photo(
    source: bytes,
    filename: str,
    settings: ImageSettings,
    templates_dir: Path,
) -> BorderedImage:
    renderer = Renderer(
        template=settings.template,
        templates_dir=templates_dir,
        width=settings.output_size,
        height=settings.output_size,
    )
    with Image.open(io.BytesIO(source)) as img:
        photo_size = img.size
    data = renderer.render_bytes(
        context={
            "width": settings.output_size,
            "height": settings.output_size,
            "border_size": settings.border_size,
            "border_color": settings.border_color,
            "shadow": settings.shadow,
            "photo_width": photo_size[0],
            "photo_height": photo_size[1],
            "image_src": _image_data_url(source, filename),
        },
    )
    return BorderedImage(data=data, size=(settings.output_size, settings.output_size))


def _image_data_url(image: bytes, filename: str) -> str:
    mime = _MIME.get(Path(filename).suffix.lower(), "image/jpeg")
    encoded = base64.b64encode(image).decode("ascii")
    return f"data:{mime};base64,{encoded}"


if __name__ == "__main__":
    from ..config import load_config

    settings = load_config()
    # settings = config.image.model_copy(update={"output_size": 600, "border_size": 20})

    sample = Path("input/test/tmel.jpg")
    out_dir = Path("output/manual")
    out_dir.mkdir(parents=True, exist_ok=True)

    result = compose_photo(
        source=sample.read_bytes(),
        filename=sample.name,
        settings=settings.image,
        templates_dir=settings.paths.templates_dir,
    )
    (out_dir / "bordered.png").write_bytes(result.data)
    print(f"Composed 1:1 image ({result.size[0]}x{result.size[1]})")
