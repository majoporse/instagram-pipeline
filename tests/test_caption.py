from openai import OpenAI

from instagram_pipeline.caption.generator import CaptionGenerator, generate_caption
from instagram_pipeline.config import CaptionSettings, OpenAISettings


class _FakeCompletions:
    def __init__(self, content: str) -> None:
        self._content = content

    def create(self, **_: object) -> object:
        from types import SimpleNamespace

        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content=self._content))
            ]
        )


class _FakeChat:
    def __init__(self, content: str) -> None:
        self.completions = _FakeCompletions(content)


class _FakeClient:
    def __init__(self, content: str) -> None:
        self.chat = _FakeChat(content)


def _stub_generator(client: OpenAI, hashtags: list[str]) -> CaptionGenerator:
    return CaptionGenerator(client=client, model="test-model", hashtags=tuple(hashtags))


def test_generate_caption_appends_hashtags() -> None:
    fake = _FakeClient("Beautiful shot under the stars")
    generator = _stub_generator(fake, ["#photography", "#stars"])

    caption = generate_caption(
        metadata={"title": "Night Sky", "location": "Chile"},
        generator=generator,
    )

    assert caption == "Beautiful shot under the stars\n\n#photography #stars"


def test_generate_caption_handles_empty_llm_response() -> None:
    fake = _FakeClient("")
    generator = _stub_generator(fake, ["#travel"])

    caption = generate_caption(metadata={}, generator=generator)

    assert caption == "\n\n#travel"


def test_from_settings_applies_base_url() -> None:
    settings = OpenAISettings(
        api_key="sk-or-v1-test",
        base_url="https://openrouter.ai/api/v1",
        model="openai/gpt-4o-mini",
    )
    generator = CaptionGenerator.from_settings(settings, CaptionSettings(hashtags=["#a"]))

    assert str(generator.model) == "openai/gpt-4o-mini"
    assert generator.hashtags == ("#a",)
    assert str(generator.client.base_url) == "https://openrouter.ai/api/v1/"


def test_from_settings_defaults_to_official_api() -> None:
    settings = OpenAISettings(api_key="sk-test", model="gpt-4o-mini")
    generator = CaptionGenerator.from_settings(settings, CaptionSettings())

    assert str(generator.client.base_url) == "https://api.openai.com/v1/"
