"""
Inference pipeline for SAR oil spill detection using ResNet34 U-Net.

Supports single-patch inference, seamless tiled inference for large GeoTIFF
satellite images with windowed overlap blending, exact spatial dimension preservation,
and configurable thresholding and normalization.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
import torch
import torch.nn.functional as F

from src.detection.preprocessing.loader import convert_to_three_channel, load_image
from src.detection.preprocessing.normalization import normalize_image
from src.detection.segmentation.model import ResNet34UNet, load_oil_spill_model

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Encapsulates the output of an oil spill inference run."""

    original_image: np.ndarray  # Displayable uint8 image (H, W, 3) or (H, W)
    probability_map: np.ndarray  # Float32 array (H, W) in [0.0, 1.0]
    binary_mask: np.ndarray  # Uint8 array (H, W) in {0, 1}
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def spill_detected(self) -> bool:
        """True if any spill pixels were detected."""
        return bool(np.any(self.binary_mask > 0))

    @property
    def spill_pixel_count(self) -> int:
        """Total number of positive spill pixels."""
        return int(np.sum(self.binary_mask > 0))

    @property
    def spill_coverage_percentage(self) -> float:
        """Percentage of total image area identified as oil spill."""
        total_pixels = self.binary_mask.size
        return float((self.spill_pixel_count / total_pixels) * 100.0) if total_pixels > 0 else 0.0


def _create_2d_window(height: int, width: int) -> np.ndarray:
    """
    Generate a 2D Hann (cosine) blending window for smooth patch stitching.

    Tapers probabilities towards tile borders, mitigating edge artifacts
    when overlapping patches are accumulated.
    """
    # 1D Hann windows
    win_h = np.hanning(height + 2)[1:-1]
    win_w = np.hanning(width + 2)[1:-1]
    # Fallback if window size is too small for hanning
    if len(win_h) == 0:
        win_h = np.ones(height, dtype=np.float32)
    if len(win_w) == 0:
        win_w = np.ones(width, dtype=np.float32)

    window_2d = np.outer(win_h, win_w).astype(np.float32)
    # Clip to avoid exact zero weights on borders
    return np.clip(window_2d, 1e-4, 1.0)


def predict_patch_direct(
    image_3ch_norm: np.ndarray,
    model: torch.nn.Module,
    device: torch.device,
) -> np.ndarray:
    """
    Run inference on a single image patch with exact dimension preservation.

    If H or W are not divisible by 32, pads the tensor symmetrically/on edges,
    computes logits, and unpads the output back to original (H, W).
    """
    h, w = image_3ch_norm.shape[:2]

    # ResNet34 has 5 downsampling stages -> dimension must be multiple of 32
    pad_h = (32 - (h % 32)) % 32
    pad_w = (32 - (w % 32)) % 32

    if pad_h > 0 or pad_w > 0:
        padded = np.pad(
            image_3ch_norm,
            ((0, pad_h), (0, pad_w), (0, 0)),
            mode="reflect",
        )
    else:
        padded = image_3ch_norm

    # Convert to PyTorch tensor (B, C, H, W)
    tensor = torch.from_numpy(padded).permute(2, 0, 1).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = model(tensor)
        probs = torch.sigmoid(logits)

    prob_map = probs[0, 0, :h, :w].cpu().numpy().astype(np.float32)
    return prob_map


def predict_tiled(
    image_3ch_norm: np.ndarray,
    model: torch.nn.Module,
    device: torch.device,
    tile_size: int = 512,
    overlap: int = 64,
    batch_size: int = 4,
) -> np.ndarray:
    """
    Perform seamless tiled inference over a large image.

    Divides the input image into overlapping tiles of size (tile_size, tile_size),
    evaluates them through the model, and blends them using a 2D window to eliminate
    patch boundaries.
    """
    h, w = image_3ch_norm.shape[:2]

    if tile_size % 32 != 0:
        raise ValueError(f"tile_size ({tile_size}) must be divisible by 32.")

    stride = tile_size - overlap
    if stride <= 0:
        raise ValueError(f"overlap ({overlap}) must be strictly smaller than tile_size ({tile_size}).")

    # If the image is smaller than or equal to tile_size in both dimensions, use direct patch
    if h <= tile_size and w <= tile_size:
        return predict_patch_direct(image_3ch_norm, model, device)

    # Compute tile coordinate ranges
    y_starts = list(range(0, max(1, h - tile_size + 1), stride))
    if len(y_starts) == 0 or y_starts[-1] + tile_size < h:
        y_starts.append(max(0, h - tile_size))

    x_starts = list(range(0, max(1, w - tile_size + 1), stride))
    if len(x_starts) == 0 or x_starts[-1] + tile_size < w:
        x_starts.append(max(0, w - tile_size))

    # Remove duplicates while preserving order
    y_starts = sorted(list(set(y_starts)))
    x_starts = sorted(list(set(x_starts)))

    prob_accum = np.zeros((h, w), dtype=np.float32)
    weight_accum = np.zeros((h, w), dtype=np.float32)
    window = _create_2d_window(tile_size, tile_size)

    tiles = []
    coords = []
    for y in y_starts:
        for x in x_starts:
            y_end = min(y + tile_size, h)
            x_end = min(x + tile_size, w)
            patch = image_3ch_norm[y:y_end, x:x_end]

            # Pad if boundary patch is smaller than tile_size
            cur_h, cur_w = patch.shape[:2]
            if cur_h < tile_size or cur_w < tile_size:
                pad_h = tile_size - cur_h
                pad_w = tile_size - cur_w
                patch = np.pad(patch, ((0, pad_h), (0, pad_w), (0, 0)), mode="reflect")

            tiles.append(patch)
            coords.append((y, x, cur_h, cur_w))

    # Process tiles in mini-batches
    total_tiles = len(tiles)
    for b_idx in range(0, total_tiles, batch_size):
        batch_tiles = tiles[b_idx : b_idx + batch_size]
        batch_coords = coords[b_idx : b_idx + batch_size]

        batch_arr = np.stack(batch_tiles, axis=0)  # (N, tile_size, tile_size, 3)
        batch_tensor = torch.from_numpy(batch_arr).permute(0, 3, 1, 2).to(device)

        with torch.no_grad():
            batch_logits = model(batch_tensor)
            batch_probs = torch.sigmoid(batch_logits).cpu().numpy()  # (N, 1, tile_size, tile_size)

        for i, (y, x, cur_h, cur_w) in enumerate(batch_coords):
            tile_prob = batch_probs[i, 0, :cur_h, :cur_w]
            tile_win = window[:cur_h, :cur_w]

            prob_accum[y : y + cur_h, x : x + cur_w] += tile_prob * tile_win
            weight_accum[y : y + cur_h, x : x + cur_w] += tile_win

    # Normalize by accumulated weights
    full_prob = prob_accum / np.maximum(weight_accum, 1e-7)
    return np.clip(full_prob, 0.0, 1.0).astype(np.float32)


def predict_oil_spill(
    image_input: Union[str, Path, np.ndarray],
    model: Optional[ResNet34UNet] = None,
    checkpoint_path: Union[str, Path] = "models/best_oil_spill_unet.pth",
    device: Optional[Union[str, torch.device]] = None,
    threshold: float = 0.5,
    norm_method: str = "percentile",
    percentile_range: Tuple[float, float] = (2.0, 98.0),
    apply_db: bool = False,
    channel_mode: str = "repeat",
    tile_size: int = 512,
    overlap: int = 64,
    use_tiling: Optional[bool] = None,
    batch_size: int = 4,
) -> PredictionResult:
    """
    End-to-end oil spill inference on an image file or NumPy array.

    Args:
        image_input: Path to image file (PNG, JPG, GeoTIFF) or raw NumPy array.
        model: Optional pre-loaded ResNet34UNet instance. If None, loaded from checkpoint_path.
        checkpoint_path: Path to checkpoint if model is not provided.
        device: 'cpu', 'cuda', or torch.device.
        threshold: Decision boundary for binary classification (default: 0.5).
        norm_method: Normalization strategy ('percentile', 'minmax', 'imagenet', 'zscore', 'none').
        percentile_range: Bounds for 'percentile' normalization.
        apply_db: Apply 10*log10(x) conversion for SAR intensity.
        channel_mode: 'repeat' to duplicate 1-channel to 3-channel.
        tile_size: Patch size for tiled inference (must be multiple of 32).
        overlap: Overlap in pixels between adjacent tiles.
        use_tiling: Force tiling on/off. If None, auto-enabled when image > tile_size.
        batch_size: Mini-batch size for tiled forward passes.

    Returns:
        PredictionResult containing original image, probability map, binary mask, and metadata.
    """
    start_time = time.perf_counter()

    # 1. Load image and metadata
    file_metadata: Dict[str, Any] = {}
    if isinstance(image_input, (str, Path)):
        raw_img, file_metadata = load_image(image_input)
    elif isinstance(image_input, np.ndarray):
        raw_img = image_input
        file_metadata = {
            "file_name": "in_memory_array",
            "format": "numpy",
            "is_geotiff": False,
            "orig_shape": raw_img.shape,
            "orig_dtype": str(raw_img.dtype),
        }
    else:
        raise TypeError(f"Unsupported image_input type: {type(image_input)}")

    orig_h, orig_w = raw_img.shape[:2]

    # Prepare displayable original image (uint8 [0, 255])
    if np.issubdtype(raw_img.dtype, np.integer) and np.max(raw_img) <= 255 and np.min(raw_img) >= 0:
        display_img = raw_img.astype(np.uint8)
    else:
        # Scale float backscatter to [0, 255] for visual display
        p2, p98 = np.percentile(raw_img, (2.0, 98.0))
        diff = p98 - p2
        clipped = np.clip(raw_img, p2, p98)
        display_img = (((clipped - p2) / (diff if diff > 1e-7 else 1.0)) * 255.0).astype(np.uint8)

    # 2. Three-channel conversion
    img_3ch = convert_to_three_channel(raw_img, mode=channel_mode)

    # 3. Normalization
    img_norm = normalize_image(
        img_3ch,
        method=norm_method,
        percentile_range=percentile_range,
        apply_db=apply_db,
    )

    # 4. Load or prepare model
    if model is None:
        model, model_metadata = load_oil_spill_model(checkpoint_path=checkpoint_path, device=device)
    else:
        model_metadata = {"device": str(next(model.parameters()).device)}

    target_device = next(model.parameters()).device

    # 5. Determine whether to use tiled inference
    if use_tiling is None:
        use_tiling = bool(orig_h > tile_size or orig_w > tile_size)

    # 6. Run inference
    inference_start = time.perf_counter()
    if use_tiling:
        prob_map = predict_tiled(
            img_norm,
            model=model,
            device=target_device,
            tile_size=tile_size,
            overlap=overlap,
            batch_size=batch_size,
        )
    else:
        prob_map = predict_patch_direct(
            img_norm,
            model=model,
            device=target_device,
        )
    inference_time_ms = (time.perf_counter() - inference_start) * 1000.0

    # 7. Generate binary segmentation mask
    binary_mask = (prob_map >= threshold).astype(np.uint8)

    total_time_ms = (time.perf_counter() - start_time) * 1000.0

    # 8. Assemble metadata
    metadata: Dict[str, Any] = {
        **file_metadata,
        "input_dimensions": (orig_h, orig_w),
        "threshold": float(threshold),
        "norm_method": norm_method,
        "channel_mode": channel_mode,
        "device": str(target_device),
        "tiled_inference": use_tiling,
        "tile_size": tile_size if use_tiling else None,
        "overlap": overlap if use_tiling else None,
        "inference_time_ms": round(inference_time_ms, 2),
        "total_time_ms": round(total_time_ms, 2),
        "prob_min": float(np.min(prob_map)),
        "prob_max": float(np.max(prob_map)),
        "prob_mean": float(np.mean(prob_map)),
        "spill_detected": bool(np.any(binary_mask > 0)),
        "spill_pixel_count": int(np.sum(binary_mask > 0)),
        "spill_coverage_percentage": round(
            float((np.sum(binary_mask > 0) / binary_mask.size) * 100.0), 4
        ),
        "model_epoch": model_metadata.get("epoch"),
        "model_best_dice": model_metadata.get("best_val_dice"),
    }

    return PredictionResult(
        original_image=display_img,
        probability_map=prob_map,
        binary_mask=binary_mask,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Convenience Chip-Level Functions (Teammate / Legacy compatibility)
# ---------------------------------------------------------------------------

def preprocess_chip(chip: np.ndarray) -> torch.Tensor:
    """
    Prepares a single SAR chip for ResNet34-UNet inference.
    
    Accepts:
      - (256, 256) single-band grayscale / SAR backscatter
      - (3, 256, 256) or (256, 256, 3) 3-channel RGB
      
    Returns:
      - torch.Tensor with shape (1, 3, 256, 256) normalized to [0, 1] float32.
    """
    arr = np.asarray(chip)
    if arr.ndim == 3 and arr.shape[-1] in (1, 3):
        arr = np.transpose(arr, (2, 0, 1))

    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=0)
    elif arr.shape[0] == 1:
        arr = np.repeat(arr, 3, axis=0)

    if arr.max() > 1.0 or arr.min() < 0.0:
        p2, p98 = np.percentile(arr, (2, 98))
        arr = np.clip((arr - p2) / (p98 - p2 + 1e-7), 0.0, 1.0)

    tensor = torch.from_numpy(arr.astype(np.float32)).unsqueeze(0)
    return tensor


@torch.no_grad()
def predict_chip(
    model: torch.nn.Module,
    chip: np.ndarray,
    prob_threshold: float = 0.50,
    device: str = "cpu",
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Runs segmentation inference on a single 256x256 chip.
    
    Returns:
      - binary_mask: (H, W) uint8 array (1 for Oil Spill, 0 for Background)
      - confidence_map: (H, W) float32 array (Probability of Oil Spill [0.0 - 1.0])
    """
    model.eval()
    x = preprocess_chip(chip).to(device)
    logits = model(x)

    if logits.shape[1] == 2:
        probs = F.softmax(logits, dim=1)[:, 1, :, :]
    else:
        probs = torch.sigmoid(logits)[:, 0, :, :]

    prob_map = probs.squeeze(0).cpu().numpy().astype(np.float32)
    binary_mask = (prob_map >= prob_threshold).astype(np.uint8)
    return binary_mask, prob_map


def run_inference_on_checkpoint(
    chip: np.ndarray,
    checkpoint_path: Union[str, Path],
    prob_threshold: float = 0.50,
    device: str = "cpu",
) -> Tuple[np.ndarray, np.ndarray]:
    """Convenience helper to load a checkpoint and run chip inference."""
    from src.detection.segmentation.model import load_model
    model = load_model(checkpoint_path=checkpoint_path, device=device)
    return predict_chip(model, chip, prob_threshold=prob_threshold, device=device)

