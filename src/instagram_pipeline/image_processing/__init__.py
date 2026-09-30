"""Pipeline images: EXIF metadata + source photo -> 1:1 bordered composition."""

from .bordered_image import BorderedImage  # noqa: F401
from .photo_metadata import (  # noqa: F401
    GpsCoordinates,
    PhotoMetadata,
    extract_gps,
    extract_metadata,
)
