"""Generate Instagram captions with the OpenAI API."""

from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI

from ..config import CaptionSettings, OpenAISettings


@dataclass(frozen=True)
class CaptionGenerator:
    """Produces an Instagram caption from photo metadata using an LLM."""

    client: OpenAI
    model: str
    hashtags: tuple[str, ...]

    @classmethod
    def from_settings(cls, settings: OpenAISettings, caption: CaptionSettings) -> CaptionGenerator:
        return cls(
            client=OpenAI(api_key=settings.api_key),
            model=settings.model,
            hashtags=tuple(caption.hashtags),
        )

    def generate(self, metadata: dict[str, object]) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write engaging Instagram captions for photography posts. "
                        "Return only the caption text, no hashtags."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Photo metadata: {metadata}",
                },
            ],
        )
        text = response.choices[0].message.content or ""
        tags = " ".join(self.hashtags)
        return f"{text.strip()}\n\n{tags}"


def generate_caption(
    metadata: dict[str, object],
    generator: CaptionGenerator,
) -> str:
    return generator.generate(metadata)


if __name__ == "__main__":
    from ..config import load_config

    config = load_config()
    generator = CaptionGenerator.from_settings(config.openai, config.caption)
    caption = generate_caption(
        metadata={
            "title": "Aurora Over the Valley",
            "location": "Reykjavik, Iceland",
            "date": "2026-09-30",
        },
        generator=generator,
    )
    print("Generated caption:\n", caption)
