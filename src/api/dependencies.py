"""
Application dependency provider and singleton model manager.

Ensures the neural network model is loaded exactly once into memory
and shared safely across API worker threads.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import torch

from src.api.config import DEFAULT_DEVICE, DEFAULT_MODEL_PATH
from src.detection.segmentation.model import ResNet34UNet, load_oil_spill_model

logger = logging.getLogger(__name__)


class ModelManager:
    """Singleton service holding the preloaded ResNet34 U-Net model and metadata."""

    _instance: Optional[ModelManager] = None

    def __init__(
        self,
        checkpoint_path: Path = DEFAULT_MODEL_PATH,
        device: Optional[str] = DEFAULT_DEVICE,
    ) -> None:
        self.checkpoint_path = checkpoint_path
        self.device_str = (
            device
            if device
            else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self.model: Optional[ResNet34UNet] = None
        self.metadata: Dict[str, Any] = {}
        self.is_loaded_status = False

    @classmethod
    def get_instance(cls) -> ModelManager:
        if cls._instance is None:
            cls._instance = ModelManager()
        return cls._instance

    def load_model(
        self,
        checkpoint_path: Optional[Path] = None,
        device: Optional[str] = None,
    ) -> Tuple[ResNet34UNet, Dict[str, Any]]:
        """Load checkpoint weights into the ResNet34UNet architecture."""
        if self.is_loaded_status and self.model is not None:
            return self.model, self.metadata

        if checkpoint_path is not None:
            self.checkpoint_path = Path(checkpoint_path)
        if device is not None:
            self.device_str = device

        logger.info("Initializing OceanTrace model from %s...", self.checkpoint_path)
        self.model, self.metadata = load_oil_spill_model(
            checkpoint_path=self.checkpoint_path,
            device=self.device_str,
            strict=True,
        )
        self.is_loaded_status = True
        logger.info(
            "Model loaded successfully on %s (Epoch: %s, Dice: %s)",
            self.device_str,
            self.metadata.get("epoch"),
            self.metadata.get("best_val_dice"),
        )
        return self.model, self.metadata

    def is_loaded(self) -> bool:
        return self.is_loaded_status and self.model is not None

    def get_model(self) -> ResNet34UNet:
        if not self.is_loaded():
            self.load_model()
        return self.model

    def get_metadata(self) -> Dict[str, Any]:
        if not self.is_loaded():
            self.load_model()
        return self.metadata

    def get_device_str(self) -> str:
        return self.device_str


ModelService = ModelManager


def get_model_manager() -> ModelManager:
    """FastAPI dependency for accessing the loaded model manager."""
    manager = ModelManager.get_instance()
    if not manager.is_loaded():
        manager.load_model()
    return manager


get_model_service = get_model_manager
