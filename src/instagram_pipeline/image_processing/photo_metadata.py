"""Extract photo metadata (GPS, camera, exposure) from EXIF data."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import exif


@dataclass(frozen=True)
class GpsCoordinates:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class PhotoMetadata:
    gps: GpsCoordinates | None = None
    camera: str | None = None
    iso: str | None = None
    shutter: str | None = None
    aperture: str | None = None
    date: str | None = None

    def context(self) -> dict[str, object]:
        location = None
        if self.gps:
            location = f"{self.gps.latitude:.4f}, {self.gps.longitude:.4f}"
        data: dict[str, object] = {
            "camera": self.camera,
            "iso": self.iso,
            "shutter": self.shutter,
            "aperture": self.aperture,
            "location": location,
            "date": self.date,
        }
        if self.gps:
            data["lat"] = self.gps.latitude
            data["lng"] = self.gps.longitude
        return data


def extract_metadata(photo: bytes) -> PhotoMetadata:
    image = exif.Image(photo)
    if not image.has_exif:
        return PhotoMetadata()
    return PhotoMetadata(
        gps=_gps(image),
        camera=_camera(image),
        iso=_iso(image),
        shutter=_shutter(image),
        aperture=_aperture(image),
        date=_date(image),
    )


def extract_gps(photo: bytes) -> GpsCoordinates | None:
    return extract_metadata(photo).gps


def _gps(image: exif.Image) -> GpsCoordinates | None:
    latitude = _decimal(image.get("gps_latitude"), image.get("gps_latitude_ref"))
    longitude = _decimal(image.get("gps_longitude"), image.get("gps_longitude_ref"))
    if latitude is None or longitude is None:
        return None
    return GpsCoordinates(latitude=latitude, longitude=longitude)


def _decimal(dms: Sequence[float], ref: object) -> float | None:
    try:
        degrees, minutes, seconds = (float(x) for x in dms)
    except (TypeError, ValueError):
        return None
    value = degrees + minutes / 60.0 + seconds / 3600.0
    if str(ref).upper() in ("S", "W"):
        value = -value
    return value


def _camera(image: exif.Image) -> str | None:
    make = image.get("make")
    model = image.get("model")
    parts = [str(part).strip() for part in (make, model) if part]
    return " ".join(parts) or None


def _iso(image: exif.Image) -> str | None:
    value = image.get("photographic_sensitivity") or image.get("iso_speed")
    return str(value) if value is not None else None


def _shutter(image: exif.Image) -> str | None:
    value = image.get("exposure_time")
    if not value:
        return None
    shutter = float(value)
    if shutter <= 0:
        return None
    if shutter >= 1:
        return f"{shutter:g}s"
    return f"1/{round(1 / shutter)}s"


def _aperture(image: exif.Image) -> str | None:
    value = image.get("f_number")
    if value is None:
        return None
    return f"f/{float(value):g}"


def _date(image: exif.Image) -> str | None:
    value = image.get("datetime_original") or image.get("datetime")
    if not value:
        return None
    return str(value).replace(":", "-", 2)


if __name__ == "__main__":
    import sys
    from pathlib import Path

    for raw in sys.argv[1:] or ["input/test/tmel.jpg"]:
        metadata = extract_metadata(Path(raw).read_bytes())
        print(f"=== {raw}")
        print(f"  gps:      {metadata.gps}")
        print(f"  camera:   {metadata.camera}")
        print(f"  iso:      {metadata.iso}")
        print(f"  shutter:  {metadata.shutter}")
        print(f"  aperture: {metadata.aperture}")
        print(f"  date:     {metadata.date}")
