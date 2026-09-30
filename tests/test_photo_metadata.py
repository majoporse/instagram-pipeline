from pathlib import Path

import exif
from PIL import Image

from instagram_pipeline.image_processing.photo_metadata import (
    GpsCoordinates,
    extract_gps,
    extract_metadata,
)


def _make_photo(tmp_path: Path, *, tagged: bool) -> Path:
    path = tmp_path / "photo.jpg"
    Image.new("RGB", (100, 100), (200, 100, 50)).save(path)
    if not tagged:
        return path

    with path.open("rb") as fh:
        image = exif.Image(fh)
    image.make = "NIKON CORPORATION"
    image.model = "NIKON D750"
    image.photographic_sensitivity = 400
    image.exposure_time = 0.005
    image.f_number = 2.8
    image.datetime_original = "2026:09:30 14:00:00"
    image.gps_latitude = (64.0, 8.0, 47.0)
    image.gps_latitude_ref = "N"
    image.gps_longitude = (21.0, 56.0, 33.0)
    image.gps_longitude_ref = "W"
    path.write_bytes(image.get_file())
    return path


def test_extract_gps_from_exif(tmp_path: Path) -> None:
    path = _make_photo(tmp_path, tagged=True)

    gps = extract_gps(path)

    assert gps is not None
    assert isinstance(gps, GpsCoordinates)
    assert abs(gps.latitude - 64.1464) < 0.001
    assert abs(gps.longitude - (-21.9425)) < 0.001


def test_extract_metadata_context(tmp_path: Path) -> None:
    path = _make_photo(tmp_path, tagged=True)

    context = extract_metadata(path).context()

    assert context["camera"] == "NIKON CORPORATION NIKON D750"
    assert context["iso"] == "400"
    assert context["shutter"] == "1/200s"
    assert context["aperture"] == "f/2.8"
    assert context["date"] == "2026-09-30 14:00:00"
    assert abs(context["lat"] - 64.1464) < 0.001  # type: ignore[operator]
    assert abs(context["lng"] - (-21.9425)) < 0.001  # type: ignore[operator]


def test_extract_metadata_missing_exif(tmp_path: Path) -> None:
    path = _make_photo(tmp_path, tagged=False)

    metadata = extract_metadata(path)
    context = metadata.context()

    assert metadata.gps is None
    assert context["camera"] is None
    assert context["iso"] is None
    assert "lat" not in context
    assert context["date"] is None
