"""Unit test for U-Net ResNet34 oil-spill segmentation on synthetic SAR chips."""
import numpy as np
import pytest
import torch

from src.detection.segmentation.model import ResNet34UNet, load_model
from src.detection.segmentation.predict import predict_chip, preprocess_chip


def test_model_forward_pass_shape():
    """Verify that (B, 3, 256, 256) tensor produces (B, 2, 256, 256) output."""
    model = ResNet34UNet(num_classes=2, in_channels=3)
    dummy_input = torch.randn(2, 3, 256, 256)
    out = model(dummy_input)
    assert out.shape == (2, 2, 256, 256), f"Expected shape (2, 2, 256, 256), got {out.shape}"


def test_predict_chip_with_synthetic_fixture(synthetic_sar_chip):
    """Verify inference pipeline on synthetic SAR backscatter chip."""
    model = load_model(checkpoint_path=None, num_classes=2, device="cpu")
    binary_mask, prob_map = predict_chip(model, synthetic_sar_chip, prob_threshold=0.50, device="cpu")

    assert binary_mask.shape == (256, 256)
    assert prob_map.shape == (256, 256)
    assert binary_mask.dtype == np.uint8
    assert prob_map.dtype == np.float32
    assert np.all((prob_map >= 0.0) & (prob_map <= 1.0))
