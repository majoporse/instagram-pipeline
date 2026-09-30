"""Instagram pipeline package."""

from .image_processing.photo_metadata import (
    GpsCoordinates,
    PhotoMetadata,
    extract_gps,
    extract_metadata,
)

__all__ = ["GpsCoordinates", "PhotoMetadata", "extract_gps", "extract_metadata"]
__version__ = "0.1.0"
