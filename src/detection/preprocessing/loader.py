"""
Image and SAR data loading utilities for OceanTrace.

Supports loading Sentinel-1 SAR GeoTIFFs, standard PNG, and JPG/JPEG files,
extracting geospatial metadata when available, and standardizing channel dimensions.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Check if rasterio is available for GeoTIFF reading
try:
    import rasterio
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False
    logger.warning("rasterio is not installed. GeoTIFF loading will fall back to PIL/Pillow.")


def load_image(
    file_path: Union[str, Path],
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Load an image from disk supporting PNG, JPG, JPEG, and GeoTIFF.

    Args:
        file_path: Path to the image file.

    Returns:
        Tuple of (image_array, metadata) where image_array is a NumPy array
        with shape (H, W) for single-channel or (H, W, C) for multi-channel,
        and metadata contains image properties, format, and geospatial tags.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path.resolve()}")

    suffix = path.suffix.lower()
    metadata: Dict[str, Any] = {
        "file_path": str(path.resolve()),
        "file_name": path.name,
        "format": suffix.lstrip("."),
        "is_geotiff": False,
        "crs": None,
        "transform": None,
        "bounds": None,
        "nodata": None,
    }

    if suffix in (".tif", ".tiff", ".geotiff") and RASTERIO_AVAILABLE:
        try:
            with rasterio.open(path) as src:
                # rasterio reads as (bands, height, width)
                data = src.read()
                metadata["is_geotiff"] = True
                metadata["crs"] = str(src.crs) if src.crs else None
                metadata["transform"] = list(src.transform) if src.transform else None
                metadata["bounds"] = (
                    [src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top]
                    if src.bounds
                    else None
                )
                metadata["nodata"] = src.nodata
                metadata["orig_shape"] = data.shape
                metadata["orig_dtype"] = str(data.dtype)

                # Reorder to (H, W) if 1-band, or (H, W, C) if multi-band
                if data.shape[0] == 1:
                    img = data[0]
                else:
                    img = np.transpose(data, (1, 2, 0))

                metadata["height"], metadata["width"] = img.shape[:2]
                metadata["channels"] = 1 if img.ndim == 2 else img.shape[2]
                return img, metadata
        except Exception as exc:
            logger.warning(
                "rasterio failed to open %s (%s). Falling back to PIL.",
                path.name,
                exc,
            )

    # Standard PIL loading for PNG, JPG, or fallback TIFF
    with Image.open(path) as pil_img:
        img = np.array(pil_img)
        metadata["height"], metadata["width"] = img.shape[:2]
        metadata["channels"] = 1 if img.ndim == 2 else img.shape[2]
        metadata["orig_shape"] = img.shape
        metadata["orig_dtype"] = str(img.dtype)

    return img, metadata


def convert_to_three_channel(
    image: np.ndarray,
    mode: str = "repeat",
) -> np.ndarray:
    """
    Ensure the input image array has 3 channels formatted as (H, W, 3).

    Args:
        image: NumPy array with shape (H, W), (H, W, 1), (1, H, W),
               (H, W, 3), (3, H, W), or (H, W, 4).
        mode: Conversion strategy for single-channel inputs:
              - 'repeat': Replicate single channel into R, G, B (standard for SAR).
              - 'zeros': Channel 0 has data, channels 1 and 2 are filled with zeros.

    Returns:
        NumPy array of shape (H, W, 3).
    """
    arr = np.asarray(image)

    # Handle (1, H, W) or (3, H, W)
    if arr.ndim == 3 and arr.shape[0] in (1, 3, 4) and arr.shape[0] < arr.shape[1]:
        arr = np.transpose(arr, (1, 2, 0))

    # Single-channel 2D (H, W)
    if arr.ndim == 2:
        if mode == "zeros":
            zeros = np.zeros_like(arr)
            return np.stack([arr, zeros, zeros], axis=-1)
        # Default 'repeat'
        return np.repeat(arr[:, :, np.newaxis], 3, axis=-1)

    # Single-channel 3D (H, W, 1)
    if arr.ndim == 3 and arr.shape[-1] == 1:
        if mode == "zeros":
            zeros = np.zeros_like(arr[:, :, 0])
            return np.stack([arr[:, :, 0], zeros, zeros], axis=-1)
        return np.repeat(arr, 3, axis=-1)

    # Multi-channel >= 3: extract first 3 channels (e.g. RGB or VV/VH/Ratio, drop alpha)
    if arr.ndim == 3:
        if arr.shape[-1] >= 3:
            return arr[:, :, :3]
        if arr.shape[-1] == 2:
            # 2-channel SAR (e.g. VV and VH): add ratio or zero as 3rd channel
            ch3 = np.zeros_like(arr[:, :, 0])
            return np.concatenate([arr, ch3[:, :, np.newaxis]], axis=-1)

    raise ValueError(f"Cannot convert image with shape {image.shape} to 3 channels.")
