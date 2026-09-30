"""Publish composed images to Instagram with instagrapi."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from instagrapi import Client
from instagrapi.types import Media

from ..config import InstagramSettings


@dataclass(frozen=True)
class Publisher:
    """Wraps an authenticated instagrapi client with session persistence."""

    client: Client
    settings: InstagramSettings

    @classmethod
    def from_settings(cls, settings: InstagramSettings) -> Publisher:
        client = Client()
        session_file = settings.session_file
        if session_file.exists():
            client.load_settings(str(session_file))
            client.login(settings.username, settings.password)
        else:
            client.login(settings.username, settings.password)
            session_file.parent.mkdir(parents=True, exist_ok=True)
            client.dump_settings(str(session_file))
        return cls(client=client, settings=settings)

    def upload(self, image: Path, caption: str) -> Media:
        return self.client.photo_upload(path=str(image), caption=caption)


def upload_image(image: Path, caption: str, publisher: Publisher) -> Media:
    return publisher.upload(image=image, caption=caption)


if __name__ == "__main__":
    from ..config import load_config

    config = load_config()
    publisher = Publisher.from_settings(config.instagram)
    caption = "A sample post from the instagram-pipeline uploader."
    media = upload_image(
        image=Path("output/manual/bordered.png"),
        caption=caption,
        publisher=publisher,
    )
    print(f"Published {media.pk} at https://instagram.com/p/{media.code}/")
