"""
ResNet34 U-Net architecture for satellite SAR oil spill segmentation.

This module implements the exact ResNet34 U-Net architecture matching the
checkpoint weights in models/best_oil_spill_unet.pth.

Architecture details:
  - Encoder: Standard torchvision ResNet-34 (conv1, bn1, relu, maxpool, layer1-layer4)
  - Decoder: 4 decoder stages (decoder4 -> decoder3 -> decoder2 -> decoder1),
    each consisting of upsampling + skip concatenation + DoubleConv block
  - Head (final_conv): Conv2d(64, 32, 3) -> BatchNorm2d(32) -> ReLU -> Conv2d(32, 1, 1)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models

logger = logging.getLogger(__name__)


class DoubleConv(nn.Module):
    """
    Two-layer convolutional block with Batch Normalization and ReLU.

    Matches the checkpoint's internal submodule:
      block.0: Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False)
      block.1: BatchNorm2d(out_channels)
      block.2: ReLU(inplace=True)
      block.3: Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False)
      block.4: BatchNorm2d(out_channels)
      block.5: ReLU(inplace=True)
    """

    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class DecoderBlock(nn.Module):
    """
    Decoder stage with feature upsampling, skip connection concatenation,
    and DoubleConv processing.
    """

    def __init__(
        self,
        in_channels: int,
        skip_channels: int,
        out_channels: int,
        upsample_mode: str = "bilinear",
        align_corners: Optional[bool] = True,
    ) -> None:
        super().__init__()
        self.upsample_mode = upsample_mode
        self.align_corners = align_corners if upsample_mode in ("bilinear", "bicubic") else None
        self.conv = DoubleConv(in_channels + skip_channels, out_channels)

    def forward(self, x: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        target_size = skip.shape[2:]
        if self.align_corners is not None:
            x = F.interpolate(x, size=target_size, mode=self.upsample_mode, align_corners=self.align_corners)
        else:
            x = F.interpolate(x, size=target_size, mode=self.upsample_mode)

        x = torch.cat([x, skip], dim=1)
        return self.conv(x)


class ResNet34UNet(nn.Module):
    """
    U-Net segmentation network with a pre-trained ResNet-34 encoder.

    Trained for binary oil-spill segmentation on satellite SAR imagery.
    """

    def __init__(
        self,
        num_classes: int = 1,
        upsample_mode: str = "bilinear",
        align_corners: Optional[bool] = True,
    ) -> None:
        super().__init__()
        self.num_classes = num_classes
        self.upsample_mode = upsample_mode
        self.align_corners = align_corners if upsample_mode in ("bilinear", "bicubic") else None

        # ResNet-34 backbone
        base = models.resnet34(weights=None)
        self.conv1 = base.conv1  # 3 -> 64
        self.bn1 = base.bn1
        self.relu = base.relu
        self.maxpool = base.maxpool
        self.layer1 = base.layer1  # 64 -> 64
        self.layer2 = base.layer2  # 64 -> 128
        self.layer3 = base.layer3  # 128 -> 256
        self.layer4 = base.layer4  # 256 -> 512

        # Decoder stages (matching checkpoint decoder4 through decoder1)
        self.decoder4 = DecoderBlock(512, 256, 256, upsample_mode, align_corners)
        self.decoder3 = DecoderBlock(256, 128, 128, upsample_mode, align_corners)
        self.decoder2 = DecoderBlock(128, 64, 64, upsample_mode, align_corners)
        self.decoder1 = DecoderBlock(64, 64, 64, upsample_mode, align_corners)

        # Output segmentation head
        self.final_conv = nn.Sequential(
            nn.Conv2d(64, 32, kernel_size=3, padding=1, bias=True),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, num_classes, kernel_size=1, bias=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Input tensor of shape (B, 3, H, W).

        Returns:
            Raw logits tensor of shape (B, num_classes, H, W).
        """
        h, w = x.shape[2:]

        # Encoder path
        x0 = self.relu(self.bn1(self.conv1(x)))  # (B, 64, H/2, W/2)
        x1 = self.layer1(self.maxpool(x0))        # (B, 64, H/4, W/4)
        x2 = self.layer2(x1)                      # (B, 128, H/8, W/8)
        x3 = self.layer3(x2)                      # (B, 256, H/16, W/16)
        x4 = self.layer4(x3)                      # (B, 512, H/32, W/32)

        # Decoder path with skip connections
        d4 = self.decoder4(x4, x3)                # (B, 256, H/16, W/16)
        d3 = self.decoder3(d4, x2)                # (B, 128, H/8, W/8)
        d2 = self.decoder2(d3, x1)                # (B, 64, H/4, W/4)
        d1 = self.decoder1(d2, x0)                # (B, 64, H/2, W/2)

        # Upsample to original input resolution and project to output classes
        if self.align_corners is not None:
            out = F.interpolate(d1, size=(h, w), mode=self.upsample_mode, align_corners=self.align_corners)
        else:
            out = F.interpolate(d1, size=(h, w), mode=self.upsample_mode)

        logits = self.final_conv(out)
        return logits


def load_oil_spill_model(
    checkpoint_path: Union[str, Path] = "models/best_oil_spill_unet.pth",
    device: Optional[Union[str, torch.device]] = None,
    strict: bool = True,
    upsample_mode: str = "bilinear",
    align_corners: Optional[bool] = True,
) -> Tuple[ResNet34UNet, Dict[str, Any]]:
    """
    Safely load the trained ResNet34 U-Net model from checkpoint.

    Args:
        checkpoint_path: Path to the .pth checkpoint file.
        device: Target execution device ('cpu', 'cuda', or torch.device).
                Defaults to auto-detect ('cuda' if available else 'cpu').
        strict: Enforce strict parameter matching in load_state_dict.
        upsample_mode: Interpolation mode used for decoder upsampling.
        align_corners: align_corners flag for bilinear/bicubic upsampling.

    Returns:
        Tuple of (model, metadata_dict) where metadata_dict contains
        checkpoint epoch, best_val_dice, and history (if present).
    """
    ckpt_file = Path(checkpoint_path)
    if not ckpt_file.exists():
        raise FileNotFoundError(f"Model checkpoint not found at: {ckpt_file.resolve()}")

    if device is None:
        target_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        target_device = torch.device(device)

    # Attempt safe weights_only loading first, fallback to standard torch.load if needed
    try:
        checkpoint = torch.load(ckpt_file, map_location=target_device, weights_only=True)
    except Exception as exc:
        logger.warning(
            "weights_only=True load failed (%s); falling back to weights_only=False.",
            exc,
        )
        checkpoint = torch.load(ckpt_file, map_location=target_device, weights_only=False)

    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        state_dict = checkpoint["model_state_dict"]
        epoch = checkpoint.get("epoch")
        best_val_dice = checkpoint.get("best_val_dice")
        history = checkpoint.get("history")
    elif isinstance(checkpoint, dict):
        state_dict = checkpoint
        epoch = None
        best_val_dice = None
        history = None
    else:
        raise TypeError(f"Unexpected checkpoint payload type: {type(checkpoint)}")

    model = ResNet34UNet(
        num_classes=1,
        upsample_mode=upsample_mode,
        align_corners=align_corners,
    )

    incompatible_keys = model.load_state_dict(state_dict, strict=strict)
    if incompatible_keys.missing_keys:
        logger.warning("Missing keys during load_state_dict: %s", incompatible_keys.missing_keys)
    if incompatible_keys.unexpected_keys:
        logger.warning("Unexpected keys during load_state_dict: %s", incompatible_keys.unexpected_keys)

    model.to(target_device)
    model.eval()

    metadata: Dict[str, Any] = {
        "epoch": epoch,
        "best_val_dice": best_val_dice,
        "history": history,
        "device": str(target_device),
        "checkpoint_path": str(ckpt_file.resolve()),
        "total_parameters": sum(p.numel() for p in model.parameters()),
        "trainable_parameters": sum(p.numel() for p in model.parameters() if p.requires_grad),
    }

    logger.info(
        "Successfully loaded ResNet34 U-Net from %s (Epoch: %s, Best Val Dice: %s) on %s",
        ckpt_file.name,
        epoch,
        f"{best_val_dice:.4f}" if best_val_dice is not None else "N/A",
        target_device,
    )

    return model, metadata
"""
U-Net with ResNet34 Encoder Model Definition & Weight Loader.
Supports PyTorch checkpoints trained on 256x256 RGB chips (Classes: Background=0, Oil Spill=1).
"""
import logging
from pathlib import Path
from typing import Optional, Union

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class DecoderBlock(nn.Module):
    """Standard U-Net decoder block: Upsample -> Concat skip -> 2x (Conv2d + BatchNorm + ReLU)."""

    def __init__(self, in_channels: int, skip_channels: int, out_channels: int):
        super().__init__()
        self.upsample = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
        total_in = (in_channels // 2) + skip_channels
        self.conv = nn.Sequential(
            nn.Conv2d(total_in, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor, skip: Optional[torch.Tensor] = None) -> torch.Tensor:
        x = self.upsample(x)
        if skip is not None:
            # Handle slight padding/dimension differences if any
            if x.shape != skip.shape:
                diff_y = skip.size()[2] - x.size()[2]
                diff_x = skip.size()[3] - x.size()[3]
                x = nn.functional.pad(x, [diff_x // 2, diff_x - diff_x // 2, diff_y // 2, diff_y - diff_y // 2])
            x = torch.cat([x, skip], dim=1)
        return self.conv(x)


class ResNet34UNet(nn.Module):
    """
    PyTorch U-Net architecture with ResNet34 feature extractor backbone.
    Accepts 3-channel input (B, 3, 256, 256) and outputs 2-class logits (B, 2, 256, 256).
    """

    def __init__(self, num_classes: int = 2, in_channels: int = 3, pretrained: bool = False):
        super().__init__()
        from torchvision.models import resnet34, ResNet34_Weights

        weights = ResNet34_Weights.DEFAULT if pretrained else None
        base = resnet34(weights=weights)

        # Encoder stages
        self.enc0 = nn.Sequential(base.conv1, base.bn1, base.relu)  # 64 channels, 128x128
        self.pool0 = base.maxpool                                   # 64 channels, 64x64
        self.enc1 = base.layer1                                     # 64 channels, 64x64
        self.enc2 = base.layer2                                     # 128 channels, 32x32
        self.enc3 = base.layer3                                     # 256 channels, 16x16
        self.enc4 = base.layer4                                     # 512 channels, 8x8

        # Decoder stages (upsampling back to 256x256)
        self.dec4 = DecoderBlock(512, 256, 256)                     # 16x16
        self.dec3 = DecoderBlock(256, 128, 128)                     # 32x32
        self.dec2 = DecoderBlock(128, 64, 64)                       # 64x64
        self.dec1 = DecoderBlock(64, 64, 64)                        # 128x128
        self.dec0 = nn.Sequential(
            nn.ConvTranspose2d(64, 32, kernel_size=2, stride=2),   # 256x256
            nn.Conv2d(32, 32, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
        )

        # Final 1x1 classification head
        self.final_conv = nn.Conv2d(32, num_classes, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Encoder passes
        e0 = self.enc0(x)       # -> (B, 64, 128, 128)
        p0 = self.pool0(e0)     # -> (B, 64, 64, 64)
        e1 = self.enc1(p0)      # -> (B, 64, 64, 64)
        e2 = self.enc2(e1)      # -> (B, 128, 32, 32)
        e3 = self.enc3(e2)      # -> (B, 256, 16, 16)
        e4 = self.enc4(e3)      # -> (B, 512, 8, 8)

        # Decoder passes with skip connections
        d4 = self.dec4(e4, e3)  # -> (B, 256, 16, 16)
        d3 = self.dec3(d4, e2)  # -> (B, 128, 32, 32)
        d2 = self.dec2(d3, e1)  # -> (B, 64, 64, 64)
        d1 = self.dec1(d2, e0)  # -> (B, 64, 128, 128)
        d0 = self.dec0(d1)      # -> (B, 32, 256, 256)

        out = self.final_conv(d0)  # -> (B, num_classes, 256, 256)
        return out


def load_model(
    checkpoint_path: Optional[Union[str, Path]] = None,
    num_classes: int = 2,
    device: str = "cpu"
) -> nn.Module:
    """
    Initializes U-Net ResNet34 and loads trained weights if provided.
    Compatible with checkpoints saved from segmentation_models_pytorch or standard PyTorch.
    """
    # 1. Check if segmentation_models_pytorch is available
    model = None
    try:
        import segmentation_models_pytorch as smp
        logger.info("Instantiating U-Net ResNet34 via segmentation_models_pytorch.")
        model = smp.Unet(
            encoder_name="resnet34",
            encoder_weights=None,
            in_channels=3,
            classes=num_classes
        )
    except ImportError:
        logger.info("segmentation_models_pytorch not installed; using native Torchvision ResNet34UNet.")
        model = ResNet34UNet(num_classes=num_classes, in_channels=3)

    if checkpoint_path and Path(checkpoint_path).exists():
        logger.info(f"Loading checkpoint weights from: {checkpoint_path}")
        state = torch.load(checkpoint_path, map_location=device)
        
        # Unpack state dictionary if wrapped inside metadata
        if isinstance(state, dict):
            if "state_dict" in state:
                state = state["state_dict"]
            elif "model_state_dict" in state:
                state = state["model_state_dict"]
            elif "model" in state:
                state = state["model"]

        # Strip 'module.' prefix if trained with DistributedDataParallel (DDP)
        clean_state = {k.replace("module.", ""): v for k, v in state.items()}
        try:
            model.load_state_dict(clean_state, strict=True)
            logger.info("Loaded weights with strict matching.")
        except Exception as e:
            logger.warning(f"Strict load failed ({e}); attempting non-strict matching...")
            model.load_state_dict(clean_state, strict=False)

    model.to(device)
    model.eval()
    return model
