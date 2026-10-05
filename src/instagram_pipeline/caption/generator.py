"""Generate Instagram captions from a photo image using an LLM vision model."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI

from ..config import CaptionSettings, OpenAISettings

_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
_SYSTEM_PROMPT = (
    "Look at the photo carefully. "
    "Output exactly 2 emojis that capture the mood of the photo "
    "and nothing else - no words, no captions, no hashtags, no punctuation."
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

    def generate(self, image: bytes, mime: str = "image/png") -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Output 2 emojis for this photo.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": self._image_data_url(image, mime),
                                "detail": "auto",
                            },
                        },
                    ],
                },
            ],
        )
        text = response.choices[0].message.content or ""
        tags = " ".join(f"#{t}" for t in self.hashtags)
        return f"{text.strip()}\n\n{tags}"

    @staticmethod
    def _image_data_url(image: bytes, mime: str) -> str:
        encoded = base64.b64encode(image).decode("ascii")
        return f"data:{mime};base64,{encoded}"


def generate_caption(
    image: bytes,
    generator: CaptionGenerator,
    mime: str = "image/png",
) -> str:
    return generator.generate(image, mime)


if __name__ == "__main__":
    from ..config import load_config

    config = load_config()
    generator = CaptionGenerator.from_settings(config.openai, config.caption)
    sample = Path("input/test/tmel.jpg")
    caption = generate_caption(
        image=sample.read_bytes(),
        generator=generator,
        mime=_MIME.get(sample.suffix.lower(), "image/jpeg"),
    )
    print("Generated caption:\n", caption)
