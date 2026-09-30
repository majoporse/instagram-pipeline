"""Generate Instagram captions from a photo image using an LLM vision model."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI

from ..config import CaptionSettings, OpenAISettings

_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
_SYSTEM_PROMPT = (
    "You write engaging Instagram captions for photography posts. "
    "Look at the photo carefully and describe it in an appealing way. "
    "Return only the caption text, no hashtags."
)


@dataclass(frozen=True)
class CaptionGenerator:
    """Produces an Instagram caption from a photo image using an LLM vision model."""

    client: OpenAI
    model: str
    hashtags: tuple[str, ...]

    @classmethod
    def from_settings(cls, settings: OpenAISettings, caption: CaptionSettings) -> CaptionGenerator:
        if settings.base_url:
            client = OpenAI(api_key=settings.api_key, base_url=settings.base_url)
        else:
            client = OpenAI(api_key=settings.api_key)
        return cls(
            client=client,
            model=settings.model,
            hashtags=tuple(caption.hashtags),
        )

    def generate(self, image: Path) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Write an Instagram caption for this photo.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": self._image_data_url(image),
                                "detail": "auto",
                            },
                        },
                    ],
                },
            ],
        )
        text = response.choices[0].message.content or ""
        tags = " ".join(self.hashtags)
        return f"{text.strip()}\n\n{tags}"

    @staticmethod
    def _image_data_url(image: Path) -> str:
        mime = _MIME.get(image.suffix.lower(), "image/jpeg")
        encoded = base64.b64encode(image.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"


def generate_caption(
    image: Path,
    generator: CaptionGenerator,
) -> str:
    return generator.generate(image)


if __name__ == "__main__":
    from ..config import load_config

    config = load_config()
    generator = CaptionGenerator.from_settings(config.openai, config.caption)
    caption = generate_caption(
        image=Path("input/test/yoda.jpg"),
        generator=generator,
    )
    print("Generated caption:\n", caption)
