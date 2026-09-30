"""Render Jinja2 HTML templates to pixel-perfect PNG images."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

from ..config import RenderSettings


@dataclass(frozen=True)
class Renderer:
    """Renders a Jinja2 template into a 1:1 PNG using headless Chromium."""

    template: str
    templates_dir: Path
    width: int = 1080
    height: int = 1080

    @classmethod
    def from_settings(cls, settings: RenderSettings, templates_dir: Path) -> Renderer:
        return cls(
            template=settings.template,
            templates_dir=templates_dir,
            width=settings.viewport_width,
            height=settings.viewport_height,
        )

    def render(self, context: dict[str, object], output: Path) -> Path:
        env = Environment(loader=FileSystemLoader(self.templates_dir))
        html = env.get_template(self.template).render(**context)

        output.parent.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(
                viewport={"width": self.width, "height": self.height},
            )
            page.set_content(html, wait_until="networkidle")
            page.screenshot(path=str(output))
            browser.close()
        return output


def render_template(
    context: dict[str, object],
    renderer: Renderer,
    output: Path,
) -> Path:
    return renderer.render(context=context, output=output)


if __name__ == "__main__":
    from ..config import load_config
    from ..image_processing.photo_metadata import extract_metadata

    config = load_config()
    renderer = Renderer.from_settings(config.render, config.paths.templates_dir)

    out = Path("output/manual/metadata_card.png")
    metadata = extract_metadata(Path("input/test/tmel.jpg"))
    result = render_template(
        context=metadata.context(),
        renderer=renderer,
        output=out,
    )
    print(f"Rendered metadata card -> {result}")
