"""Compose a source photo into an exact 1:1 image with a border."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

from ..config import ImageSettings

SUPPORTED_RATIO = 1.0


@dataclass(frozen=True)
class BorderedImage:
    """Result of the 1:1 composition step."""

    path: Path
    size: tuple[int, int]


def compose_photo(source: Path, output: Path, settings: ImageSettings) -> BorderedImage:
    src: Image.Image = Image.open(source)
    img: Image.Image = ImageOps.exif_transpose(src).convert("RGB")

    target = settings.output_size
    border = settings.border_size
    inner = target - (border * 2)

    img = ImageOps.fit(img, (inner, inner), method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (target, target), settings.border_color)
    canvas.paste(img, (border, border))

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="JPEG", quality=settings.jpeg_quality)
    return BorderedImage(path=output, size=(target, target))


if __name__ == "__main__":
    from ..config import load_config

    config = load_config()
    settings = config.image.model_copy(
        update={"output_size": 600, "border_size": 20, "border_color": "#1d3557"}
    )

    sample_dir = Path("output/manual")
    sample_dir.mkdir(parents=True, exist_ok=True)

    sample = Image.new("RGB", (400, 300), (100, 149, 237))
    sample.save(sample_dir / "source_sample.jpg", quality=95)

    result = compose_photo(
        source=sample_dir / "source_sample.jpg",
        output=sample_dir / "bordered.jpg",
        settings=settings,
    )
    print(f"Composed 1:1 image -> {result.path} ({result.size[0]}x{result.size[1]})")
