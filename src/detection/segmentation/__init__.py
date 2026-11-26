"""Segmentation sub-package: YOLO model wrapper, ResNet34 U-Net, dataset loader, inference."""

from src.detection.segmentation.model import (
    DecoderBlock,
    DoubleConv,
    ResNet34UNet,
    load_model,
    load_oil_spill_model,
)
from src.detection.segmentation.predict import (
    PredictionResult,
    predict_chip,
    predict_oil_spill,
    predict_patch_direct,
    predict_tiled,
    preprocess_chip,
    run_inference_on_checkpoint,
)

__all__ = [
    "ResNet34UNet",
    "DoubleConv",
    "DecoderBlock",
    "load_oil_spill_model",
    "load_model",
    "PredictionResult",
    "predict_oil_spill",
    "predict_patch_direct",
    "predict_tiled",
    "predict_chip",
    "preprocess_chip",
    "run_inference_on_checkpoint",
]



