from pathlib import Path

from PIL import Image

from instagram_pipeline.config import ImageSettings, PathSettings
from instagram_pipeline.image_processing.bordered_image import (
    BorderedImage,
    compose_photo,
)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _settings(
    output_size: int = 600,
    border_size: int = 30,
    shadow: bool = False,
) -> ImageSettings:
    return ImageSettings(
        output_size=output_size,
        border_size=border_size,
        border_color="#123456",
        shadow=shadow,
    )


def _paths() -> PathSettings:
    return PathSettings(templates_dir=TEMPLATES_DIR)


def test_compose_photo_creates_exact_square(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (400, 300), (200, 100, 50)).save(source)

    out = tmp_path / "bordered.png"
    result = compose_photo(source=source, output=out, settings=_settings(), paths=_paths())

    assert isinstance(result, BorderedImage)
    assert result.size == (600, 600)

    with Image.open(out) as img:
        assert img.size == (600, 600)


def test_compose_photo_preserves_aspect_ratio(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (400, 300), (200, 100, 50)).save(source)

    out = tmp_path / "bordered.png"
    compose_photo(source=source, output=out, settings=_settings(), paths=_paths())

    with Image.open(out) as img:
        bg_px = img.getpixel((0, 0))
        assert isinstance(bg_px, tuple) and len(bg_px) == 3
        bg: tuple[int, int, int] = (bg_px[0], bg_px[1], bg_px[2])
        photo_bbox = _photo_bbox(img, bg)
        assert photo_bbox is not None

    x0, y0, x1, y1 = photo_bbox
    w = x1 - x0
    h = y1 - y0
    assert w > 0 and h > 0
    assert abs((w / h) - (400 / 300)) < 0.05


def test_compose_photo_is_centered(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (400, 300), (200, 100, 50)).save(source)

    settings = _settings()
    out = tmp_path / "bordered.png"
    compose_photo(source=source, output=out, settings=settings, paths=_paths())

    size = settings.output_size
    with Image.open(out) as img:
        bg_px = img.getpixel((0, 0))
        assert isinstance(bg_px, tuple) and len(bg_px) == 3
        bg: tuple[int, int, int] = (bg_px[0], bg_px[1], bg_px[2])
        photo_bbox = _photo_bbox(img, bg)
        assert photo_bbox is not None

    x0, y0, x1, y1 = photo_bbox
    assert abs(x0 - (size - x1)) <= 20
    assert abs(y0 - (size - y1)) <= 20


def test_compose_photo_scales_to_fit_inner_box(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 50), (200, 100, 50)).save(source)

    settings = _settings()
    out = tmp_path / "bordered.png"
    compose_photo(source=source, output=out, settings=settings, paths=_paths())

    with Image.open(out) as img:
        bg_px = img.getpixel((0, 0))
        assert isinstance(bg_px, tuple) and len(bg_px) == 3
        bg: tuple[int, int, int] = (bg_px[0], bg_px[1], bg_px[2])
        photo_bbox = _photo_bbox(img, bg)
        assert photo_bbox is not None

    max_inner = settings.output_size - (settings.border_size * 2)

    x0, y0, x1, y1 = photo_bbox
    w = x1 - x0
    h = y1 - y0
    assert w > 0 and h > 0
    assert max(w, h) == max_inner
    assert abs((w / h) - (100 / 50)) < 0.05


def test_compose_photo_renders_shadow(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (100, 50), (200, 100, 50)).save(source)

    plain_out = tmp_path / "plain.png"
    compose_photo(source=source, output=plain_out, settings=_settings(), paths=_paths())

    styled_out = tmp_path / "styled.png"
    compose_photo(
        source=source,
        output=styled_out,
        settings=_settings(shadow=True),
        paths=_paths(),
    )

    with Image.open(plain_out) as plain, Image.open(styled_out) as styled:
        plain_conv = plain.convert("RGB")
        styled_conv = styled.convert("RGB")
        frame = styled_conv.getpixel((0, 0))
        assert isinstance(frame, tuple)
        assert plain_conv.tobytes() != styled_conv.tobytes()

    brighter = 0
    for y in range(0, styled_conv.height):
        for x in range(0, styled_conv.width, 4):
            p = styled_conv.getpixel((x, y))
            if isinstance(p, tuple) and sum(p) > sum(frame) + 100:
                brighter += 1
    assert brighter > 0


def _photo_bbox(
    img: Image.Image, bg: tuple[int, int, int]
) -> tuple[int, int, int, int] | None:
    xs: list[int] = []
    ys: list[int] = []
    width, height = img.size
    for y in range(0, height, 2):
        for x in range(0, width, 2):
            p = img.getpixel((x, y))
            assert isinstance(p, tuple)
            if abs(p[0] - bg[0]) + abs(p[1] - bg[1]) + abs(p[2] - bg[2]) > 5:
                xs.append(x)
                ys.append(y)
    if not xs or not ys:
        return None
    return min(xs), min(ys), max(xs) + 2, max(ys) + 2
