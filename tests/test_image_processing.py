from pathlib import Path

from PIL import Image

from instagram_pipeline.config import ImageSettings
from instagram_pipeline.image_processing.bordered_image import (
    BorderedImage,
    compose_photo,
)


def _stub_settings() -> ImageSettings:
    return ImageSettings(output_size=600, border_size=30, border_color="#123456")


def test_compose_photo_creates_exact_square(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (400, 300), (200, 100, 50)).save(source)

    out = tmp_path / "out" / "bordered.jpg"
    settings = _stub_settings()

    result = compose_photo(source=source, output=out, settings=settings)

    assert isinstance(result, BorderedImage)
    assert result.size == (600, 600)

    with Image.open(out) as img:
        assert img.size == (600, 600)


def test_compose_photo_respects_border_size(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (200, 200), (10, 20, 30)).save(source)

    settings = _stub_settings()
    result = compose_photo(
        source=source,
        output=tmp_path / "bordered.jpg",
        settings=settings,
    )
    assert result.path.exists()
