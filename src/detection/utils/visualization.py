"""
Visualization utilities for SAR oil spill detection.

Generates 3-panel comparison figures (Original SAR | Probability Map | Detection Overlay)
and blends predicted segmentation masks over satellite imagery.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend suitable for headless servers/CLI
import matplotlib.pyplot as plt
import numpy as np


def create_overlay(
    original_image: np.ndarray,
    binary_mask: np.ndarray,
    color: Tuple[int, int, int] = (255, 30, 30),  # Bright red
    alpha: float = 0.45,
) -> np.ndarray:
    """
    Blend a binary spill mask onto an image with customizable color and transparency.

    Args:
        original_image: uint8 array with shape (H, W) or (H, W, 3).
        binary_mask: uint8 array with shape (H, W) in {0, 1}.
        color: RGB tuple for positive mask pixels (default: bright red).
        alpha: Transparency factor between 0.0 (transparent) and 1.0 (opaque).

    Returns:
        uint8 RGB array of shape (H, W, 3) with the blended overlay.
    """
    # Ensure original is 3-channel uint8
    if original_image.ndim == 2:
        base = np.repeat(original_image[:, :, np.newaxis], 3, axis=-1)
    else:
        base = original_image[:, :, :3].copy()

    if base.dtype != np.uint8:
        base = np.clip(base, 0, 255).astype(np.uint8)

    overlay = base.copy().astype(np.float32)
    mask_bool = binary_mask > 0

    if np.any(mask_bool):
        color_arr = np.array(color, dtype=np.float32)
        # Linear alpha blending on mask pixels
        overlay[mask_bool] = (1.0 - alpha) * overlay[mask_bool] + alpha * color_arr

    return np.clip(overlay, 0, 255).astype(np.uint8)


def create_prediction_figure(
    original_image: np.ndarray,
    probability_map: np.ndarray,
    binary_mask: np.ndarray,
    metadata: Optional[Dict[str, Any]] = None,
    figsize: Tuple[int, int] = (16, 5),
    dpi: int = 150,
) -> plt.Figure:
    """
    Create a publication-quality 3-panel figure:
    [Original SAR Image] | [Probability Map] | [Oil Spill Overlay]
    """
    fig, axes = plt.subplots(1, 3, figsize=figsize, dpi=dpi)

    # 1. Original Image
    if original_image.ndim == 2 or (original_image.ndim == 3 and original_image.shape[-1] == 1):
        axes[0].imshow(np.squeeze(original_image), cmap="gray")
    else:
        axes[0].imshow(original_image)
    axes[0].set_title("1. Original SAR Scene", fontsize=12, fontweight="bold")
    axes[0].axis("off")

    # 2. Probability Heatmap
    im_prob = axes[1].imshow(probability_map, cmap="inferno", vmin=0.0, vmax=1.0)
    axes[1].set_title("2. Spill Probability Map", fontsize=12, fontweight="bold")
    axes[1].axis("off")
    cbar = fig.colorbar(im_prob, ax=axes[1], fraction=0.046, pad=0.04)
    cbar.ax.tick_params(labelsize=9)

    # 3. Blended Overlay
    overlay_img = create_overlay(original_image, binary_mask)
    axes[2].imshow(overlay_img)

    # Overlay subtitle / status
    spill_detected = bool(np.any(binary_mask > 0))
    status_text = "SPILL DETECTED" if spill_detected else "NO SPILL DETECTED"
    status_color = "red" if spill_detected else "green"

    axes[2].set_title(f"3. Detection Overlay ({status_text})", fontsize=12, fontweight="bold", color=status_color)
    axes[2].axis("off")

    # Top title with key metadata
    meta_str = ""
    if metadata:
        thresh = metadata.get("threshold", 0.5)
        cov = metadata.get("spill_coverage_percentage", 0.0)
        time_ms = metadata.get("inference_time_ms", 0.0)
        meta_str = f" | Threshold: {thresh:.2f} | Coverage: {cov:.2f}% | Latency: {time_ms:.1f}ms"

    fig.suptitle(f"OceanTrace — Oil Spill Detection (ResNet34 U-Net){meta_str}", fontsize=13, y=0.98)
    fig.tight_layout()
    return fig


def save_prediction_visualization(
    figure: plt.Figure,
    output_path: Union[str, Path],
    dpi: int = 150,
) -> Path:
    """Save the matplotlib figure to an image file and close the figure."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(out, dpi=dpi, bbox_inches="tight")
    plt.close(figure)
    return out
