from pathlib import Path

from instagram_pipeline.caption.generator import CaptionGenerator, generate_caption
from instagram_pipeline.config import CaptionSettings, OpenAISettings


class _FakeCompletions:
    def __init__(self, content: str) -> None:
        self._content = content
        self.seen_content: list[object] | None = None

    def create(self, **kwargs: object) -> object:
        from types import SimpleNamespace

        self.seen_content = kwargs.get("messages")  # type: ignore[assignment]
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


def _stub_generator(client: object, hashtags: list[str]) -> CaptionGenerator:
    return CaptionGenerator(
        client=client,  # type: ignore[arg-type]
        model="test-model",
        hashtags=tuple(hashtags),
    )


def test_generate_caption_appends_hashtags(tmp_path: Path) -> None:
    fake = _FakeClient("Beautiful shot under the stars")
    generator = _stub_generator(fake, ["photography", "stars"])
    image = tmp_path / "photo.png"
    image.write_bytes(b"fake-image-bytes")

    caption = generate_caption(image=image.read_bytes(), generator=generator)

    assert caption == "Beautiful shot under the stars\n\n#photography #stars"


def test_generate_caption_handles_empty_llm_response(tmp_path: Path) -> None:
    fake = _FakeClient("")
    generator = _stub_generator(fake, ["travel"])
    image = tmp_path / "photo.jpg"
    image.write_bytes(b"fake-image-bytes")

    caption = generate_caption(
        image=image.read_bytes(), generator=generator, mime="image/jpeg"
    )

    assert caption == "\n\n#travel"


def test_generate_caption_sends_image_data_url(tmp_path: Path) -> None:
    import base64

    fake = _FakeClient("Nice")
    generator = _stub_generator(fake, [])
    image = tmp_path / "photo.png"
    image_bytes = b"fake-image-bytes"
    image.write_bytes(image_bytes)

    generate_caption(image=image_bytes, generator=generator)

    messages = fake.chat.completions.seen_content
    assert messages is not None
    user_message = messages[1]  # type: ignore[index]
    content = user_message["content"]  # type: ignore[index]
    assert isinstance(content, list)
    image_part = content[1]
    assert "image_url" in image_part  # type: ignore[operator]
    url = image_part["image_url"]["url"]  # type: ignore[index]
    expected_b64 = base64.b64encode(image_bytes).decode("ascii")
    assert url == f"data:image/png;base64,{expected_b64}"


def test_from_settings_applies_base_url() -> None:
    settings = OpenAISettings(
        api_key="sk-or-v1-test",
        base_url="https://openrouter.ai/api/v1",
        model="openai/gpt-4o-mini",
    )
    generator = CaptionGenerator.from_settings(settings, CaptionSettings(hashtags=["a"]))

    assert str(generator.model) == "openai/gpt-4o-mini"
    assert generator.hashtags == ("a",)
    assert str(generator.client.base_url) == "https://openrouter.ai/api/v1/"


def test_from_settings_defaults_to_official_api() -> None:
    settings = OpenAISettings(api_key="sk-test", model="gpt-4o-mini")
    generator = CaptionGenerator.from_settings(settings, CaptionSettings())

    assert str(generator.client.base_url) == "https://api.openai.com/v1/"
