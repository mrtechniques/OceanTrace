"""
Inference pipeline for U-Net ResNet34 oil-spill segmentation on 256x256 image chips.
"""
from pathlib import Path
from typing import Tuple, Union

import numpy as np
import torch
import torch.nn.functional as F

from src.detection.segmentation.model import load_model


def preprocess_chip(chip: np.ndarray) -> torch.Tensor:
    """
    Prepares a single SAR chip for ResNet34-UNet inference.
    
    Accepts:
      - (256, 256) single-band grayscale / SAR backscatter
      - (3, 256, 256) or (256, 256, 3) 3-channel RGB
      
    Returns:
      - torch.Tensor with shape (1, 3, 256, 256) normalized to [0, 1] float32.
    """
    # If channel last (256, 256, C), transpose to (C, 256, 256)
    if chip.ndim == 3 and chip.shape[-1] in (1, 3):
        chip = np.transpose(chip, (2, 0, 1))

    # If single-channel (256, 256) or (1, 256, 256), repeat to 3 channels for ResNet34
    if chip.ndim == 2:
        chip = np.stack([chip, chip, chip], axis=0)
    elif chip.shape[0] == 1:
        chip = np.repeat(chip, 3, axis=0)

    # Standard min-max percentile scaling to [0, 1] if not already normalized
    if chip.max() > 1.0 or chip.min() < 0.0:
        p2, p98 = np.percentile(chip, (2, 98))
        chip = np.clip((chip - p2) / (p98 - p2 + 1e-7), 0.0, 1.0)

    tensor = torch.from_numpy(chip.astype(np.float32)).unsqueeze(0)  # Shape (1, 3, 256, 256)
    return tensor


@torch.no_grad()
def predict_chip(
    model: torch.nn.Module,
    chip: np.ndarray,
    prob_threshold: float = 0.50,
    device: str = "cpu"
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Runs segmentation inference on a 256x256 chip.
    
    Returns:
      - binary_mask: (256, 256) uint8 array (1 for Oil Spill, 0 for Background)
      - confidence_map: (256, 256) float32 array (Probability of Oil Spill [0.0 - 1.0])
    """
    model.eval()
    x = preprocess_chip(chip).to(device)

    logits = model(x)  # Shape (1, 2, 256, 256)
    
    if logits.shape[1] == 2:
        # 2-class softmax: class 0 is Background, class 1 is Oil Spill
        probs = F.softmax(logits, dim=1)[:, 1, :, :]
    else:
        # Single-class sigmoid
        probs = torch.sigmoid(logits)[:, 0, :, :]

    prob_map = probs.squeeze(0).cpu().numpy()  # (256, 256)
    binary_mask = (prob_map >= prob_threshold).astype(np.uint8)

    return binary_mask, prob_map


def run_inference_on_checkpoint(
    chip: np.ndarray,
    checkpoint_path: Union[str, Path],
    prob_threshold: float = 0.50,
    device: str = "cpu"
) -> Tuple[np.ndarray, np.ndarray]:
    """Convenience helper to load a checkpoint and run inference in one call."""
    model = load_model(checkpoint_path=checkpoint_path, num_classes=2, device=device)
    return predict_chip(model, chip, prob_threshold=prob_threshold, device=device)
