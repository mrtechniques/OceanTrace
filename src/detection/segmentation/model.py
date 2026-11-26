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
