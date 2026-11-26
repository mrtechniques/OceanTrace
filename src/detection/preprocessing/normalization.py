"""
Configurable normalization schemes for SAR backscatter and optical imagery.

NOTE ON TRAINING PREPROCESSING:
The exact normalization scheme used during model training was not stored in the
checkpoint dictionary. Therefore, this module provides multiple configurable
normalization strategies so users can evaluate or select the appropriate pipeline.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)

# Standard ImageNet statistics (often used with pretrained ResNet backbones)
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def normalize_image(
    image: np.ndarray,
    method: str = "percentile",
    percentile_range: Tuple[float, float] = (2.0, 98.0),
    apply_db: bool = False,
    eps: float = 1e-7,
) -> np.ndarray:
    """
    Normalize image data to float32 suitable for neural network input.

    Supported methods:
      - 'percentile': Clips extreme backscatter outliers at (p_low, p_high) percentiles
                      and scales linearly to [0.0, 1.0]. Robust for SAR speckle.
      - 'minmax': Scales linearly using minimum and maximum values to [0.0, 1.0].
      - 'imagenet': Scales image to [0.0, 1.0] and applies standard ImageNet
                    channel-wise mean subtraction and standard deviation scaling.
      - 'zscore': Standardizes each channel to zero-mean and unit-variance (x - mean) / std.
      - 'none': Converts to float32 without scaling (or divides uint8 [0, 255] by 255.0).

    Args:
        image: Input array of shape (H, W) or (H, W, C).
        method: Normalization strategy ('percentile', 'minmax', 'imagenet', 'zscore', 'none').
        percentile_range: Tuple of (low_percentile, high_percentile) for 'percentile' method.
        apply_db: If True, applies decibel conversion 10 * log10(x + eps) before scaling.
                  Useful for linear SAR intensity/sigma0 imagery.
        eps: Small constant to avoid division by zero or log of zero.

    Returns:
        Normalized NumPy float32 array with identical shape to input.
    """
    arr = np.asarray(image, dtype=np.float32)

    # Optional decibel transformation for linear SAR amplitude/power
    if apply_db:
        arr = np.maximum(arr, eps)
        arr = 10.0 * np.log10(arr)

    method = method.lower()

    if method == "percentile":
        p_low, p_high = percentile_range
        # Compute percentiles per-channel if multi-channel, or globally
        if arr.ndim == 3:
            norm_channels = []
            for c in range(arr.shape[-1]):
                ch = arr[:, :, c]
                v_min = np.percentile(ch, p_low)
                v_max = np.percentile(ch, p_high)
                ch_clipped = np.clip(ch, v_min, v_max)
                diff = v_max - v_min
                norm_ch = (ch_clipped - v_min) / (diff if diff > eps else 1.0)
                norm_channels.append(norm_ch)
            return np.stack(norm_channels, axis=-1).astype(np.float32)
        else:
            v_min = np.percentile(arr, p_low)
            v_max = np.percentile(arr, p_high)
            clipped = np.clip(arr, v_min, v_max)
            diff = v_max - v_min
            return ((clipped - v_min) / (diff if diff > eps else 1.0)).astype(np.float32)

    elif method == "minmax":
        if arr.ndim == 3:
            norm_channels = []
            for c in range(arr.shape[-1]):
                ch = arr[:, :, c]
                v_min = np.min(ch)
                v_max = np.max(ch)
                diff = v_max - v_min
                norm_ch = (ch - v_min) / (diff if diff > eps else 1.0)
                norm_channels.append(norm_ch)
            return np.stack(norm_channels, axis=-1).astype(np.float32)
        else:
            v_min = np.min(arr)
            v_max = np.max(arr)
            diff = v_max - v_min
            return ((arr - v_min) / (diff if diff > eps else 1.0)).astype(np.float32)

    elif method == "imagenet":
        # First ensure in [0.0, 1.0]
        v_min, v_max = np.min(arr), np.max(arr)
        if v_max > 1.0 or v_min < 0.0:
            diff = v_max - v_min
            scaled = (arr - v_min) / (diff if diff > eps else 1.0)
        else:
            scaled = arr

        # Apply ImageNet normalization per channel
        if scaled.ndim == 3 and scaled.shape[-1] == 3:
            norm_arr = (scaled - IMAGENET_MEAN) / IMAGENET_STD
            return norm_arr.astype(np.float32)
        elif scaled.ndim == 2:
            norm_arr = (scaled - IMAGENET_MEAN[0]) / IMAGENET_STD[0]
            return norm_arr.astype(np.float32)
        else:
            return scaled.astype(np.float32)

    elif method == "zscore":
        if arr.ndim == 3:
            norm_channels = []
            for c in range(arr.shape[-1]):
                ch = arr[:, :, c]
                mean = np.mean(ch)
                std = np.std(ch)
                norm_ch = (ch - mean) / (std if std > eps else 1.0)
                norm_channels.append(norm_ch)
            return np.stack(norm_channels, axis=-1).astype(np.float32)
        else:
            mean = np.mean(arr)
            std = np.std(arr)
            return ((arr - mean) / (std if std > eps else 1.0)).astype(np.float32)

    elif method == "none":
        # If integer uint8, scale to [0, 1] float
        if np.issubdtype(image.dtype, np.integer) and np.max(arr) > 1.0:
            return (arr / 255.0).astype(np.float32)
        return arr.astype(np.float32)

    else:
        raise ValueError(
            f"Unsupported normalization method '{method}'. "
            f"Choose from: 'percentile', 'minmax', 'imagenet', 'zscore', 'none'."
        )
