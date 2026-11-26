"""
Unit tests for the ResNet34 U-Net model and checkpoint loading utility.
"""

from pathlib import Path

import numpy as np
import pytest
import torch

from src.detection.segmentation.model import (
    DecoderBlock,
    DoubleConv,
    ResNet34UNet,
    load_oil_spill_model,
)

CHECKPOINT_PATH = Path("models/best_oil_spill_unet.pth")


def test_double_conv_block():
    """Verify DoubleConv layer architecture, parameters, and output shape."""
    block = DoubleConv(in_channels=64, out_channels=32)
    x = torch.randn(2, 64, 32, 32)
    out = block(x)

    assert out.shape == (2, 32, 32, 32)
    assert len(block.block) == 6
    assert isinstance(block.block[0], torch.nn.Conv2d)
    assert block.block[0].bias is None  # Followed by BatchNorm2d
    assert isinstance(block.block[1], torch.nn.BatchNorm2d)
    assert isinstance(block.block[2], torch.nn.ReLU)
    assert isinstance(block.block[3], torch.nn.Conv2d)
    assert block.block[3].bias is None
    assert isinstance(block.block[4], torch.nn.BatchNorm2d)
    assert isinstance(block.block[5], torch.nn.ReLU)


def test_decoder_block():
    """Verify DecoderBlock upsampling, skip concatenation, and output shape."""
    decoder = DecoderBlock(
        in_channels=512,
        skip_channels=256,
        out_channels=256,
        upsample_mode="bilinear",
        align_corners=True,
    )
    x = torch.randn(1, 512, 8, 8)
    skip = torch.randn(1, 256, 16, 16)
    out = decoder(x, skip)

    assert out.shape == (1, 256, 16, 16)


def test_unet_instantiation():
    """Verify ResNet34UNet instantiates properly with all required layers."""
    model = ResNet34UNet(num_classes=1)

    assert hasattr(model, "conv1")
    assert hasattr(model, "bn1")
    assert hasattr(model, "layer1")
    assert hasattr(model, "layer2")
    assert hasattr(model, "layer3")
    assert hasattr(model, "layer4")
    assert hasattr(model, "decoder4")
    assert hasattr(model, "decoder3")
    assert hasattr(model, "decoder2")
    assert hasattr(model, "decoder1")
    assert hasattr(model, "final_conv")

    total_params = sum(p.numel() for p in model.parameters())
    assert total_params > 20_000_000  # Expected ~24.4M params


def test_unet_forward_synthetic_3channel():
    """Verify forward pass on a synthetic 256x256, 3-channel input."""
    model = ResNet34UNet(num_classes=1)
    model.eval()

    with torch.no_grad():
        x = torch.randn(1, 3, 256, 256)
        logits = model(x)
        probs = torch.sigmoid(logits)

    assert logits.shape == (1, 1, 256, 256)
    assert torch.isfinite(logits).all().item() is True
    assert ((probs >= 0.0) & (probs <= 1.0)).all().item() is True


def test_unet_forward_from_conftest_sar_fixture(synthetic_sar_chip):
    """Verify inference using the existing conftest synthetic_sar_chip fixture."""
    model = ResNet34UNet(num_classes=1)
    model.eval()

    # synthetic_sar_chip is (1, 256, 256) float32; expand to 3 channels for ResNet34
    sar_3ch = np.repeat(synthetic_sar_chip, 3, axis=0)  # (3, 256, 256)
    x = torch.from_numpy(sar_3ch).unsqueeze(0)  # (1, 3, 256, 256)

    with torch.no_grad():
        logits = model(x)
        probs = torch.sigmoid(logits)

    assert logits.shape == (1, 1, 256, 256)
    assert torch.isfinite(logits).all().item() is True
    assert ((probs >= 0.0) & (probs <= 1.0)).all().item() is True


@pytest.mark.skipif(not CHECKPOINT_PATH.exists(), reason="Checkpoint file not found")
def test_load_oil_spill_model_strict():
    """Verify checkpoint loads with strict=True and exact metadata match."""
    model, metadata = load_oil_spill_model(
        checkpoint_path=CHECKPOINT_PATH,
        device="cpu",
        strict=True,
    )

    assert isinstance(model, ResNet34UNet)
    assert metadata["epoch"] == 14
    assert pytest.approx(metadata["best_val_dice"], rel=1e-4) == 0.8255
    assert metadata["device"] == "cpu"
    assert metadata["total_parameters"] > 20_000_000


@pytest.mark.skipif(not CHECKPOINT_PATH.exists(), reason="Checkpoint file not found")
def test_checkpoint_keys_exact_match():
    """Verify that every single parameter key in the checkpoint matches the model state dict."""
    ckpt = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=False)
    ckpt_state = ckpt["model_state_dict"]

    model = ResNet34UNet(num_classes=1)
    model_state = model.state_dict()

    missing_keys = set(ckpt_state.keys()) - set(model_state.keys())
    unexpected_keys = set(model_state.keys()) - set(ckpt_state.keys())

    assert len(missing_keys) == 0, f"Missing keys in model: {missing_keys}"
    assert len(unexpected_keys) == 0, f"Unexpected keys in model: {unexpected_keys}"
    assert len(ckpt_state) == 273

    # Check that shapes match exactly
    for key, weight in ckpt_state.items():
        assert model_state[key].shape == weight.shape, (
            f"Shape mismatch for {key}: {model_state[key].shape} vs {weight.shape}"
        )


@pytest.mark.skipif(not CHECKPOINT_PATH.exists(), reason="Checkpoint file not found")
def test_loaded_model_inference_pipeline():
    """Verify inference pipeline with the actual loaded checkpoint."""
    model, metadata = load_oil_spill_model(
        checkpoint_path=CHECKPOINT_PATH,
        device="cpu",
        strict=True,
    )

    x = torch.randn(1, 3, 256, 256)
    with torch.no_grad():
        logits = model(x)
        probs = torch.sigmoid(logits)
        mask = (probs > 0.5).to(torch.uint8)

    assert logits.shape == (1, 1, 256, 256)
    assert probs.shape == (1, 1, 256, 256)
    assert mask.shape == (1, 1, 256, 256)
    assert torch.isfinite(logits).all().item() is True
    assert ((probs >= 0.0) & (probs <= 1.0)).all().item() is True
    assert set(torch.unique(mask).tolist()).issubset({0, 1})


def test_variable_input_resolutions():
    """Verify model can handle various resolutions divisible by 32."""
    model = ResNet34UNet(num_classes=1)
    model.eval()

    for size in (128, 512):
        with torch.no_grad():
            x = torch.randn(1, 3, size, size)
            out = model(x)
            assert out.shape == (1, 1, size, size)
            assert torch.isfinite(out).all().item() is True
