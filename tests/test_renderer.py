from pathlib import Path

from PIL import Image

from instagram_pipeline.config import TEMPLATES_DIR, RenderSettings
from instagram_pipeline.renderer.renderer import Renderer, render_template


def test_render_template_produces_png(tmp_path: Path) -> None:
    renderer = Renderer(
        template="metadata.html",
        templates_dir=TEMPLATES_DIR,
        width=1080,
        height=1080,
    )

    out = tmp_path / "card.png"
    result = render_template(
        context={
            "camera": "NIKON D750",
            "iso": "400",
            "shutter": "1/200s",
            "aperture": "f/2.8",
            "location": "Reykjavik, Iceland",
            "date": "2026-09-30",
        },
        renderer=renderer,
        output=out,
    )

    assert result == out
    assert out.exists()

    with Image.open(out) as img:
        assert img.format == "PNG"
        assert img.size == (1080, 1080)


def test_renderer_from_settings_uses_config() -> None:
    settings = RenderSettings(template="metadata.html")
    renderer = Renderer.from_settings(settings, TEMPLATES_DIR)
    assert renderer.template == "metadata.html"
    assert renderer.templates_dir == TEMPLATES_DIR
    assert (renderer.width, renderer.height) == (1080, 1080)
