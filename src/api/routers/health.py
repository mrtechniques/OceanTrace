"""
Health and status check router for the OceanTrace API.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends

from src.api.dependencies import ModelService, get_model_service
from src.api.schemas import EvaluationMetrics, HealthResponse, ModelInfoResponse

router = APIRouter(tags=["Health & Model Info"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System and Model Health Status",
    description="Returns backend uptime, loaded model metadata, and hardware execution device.",
)
async def get_health(
    model_service: ModelService = Depends(get_model_service),
) -> HealthResponse:
    """Check backend operational status and neural network state."""
    is_ready = model_service.is_loaded()
    meta = model_service.get_metadata()

    return HealthResponse(
        status="healthy" if is_ready else "degraded",
        model_loaded=is_ready,
        model_name="ResNet34UNet",
        model_epoch=meta.get("epoch"),
        model_best_dice=meta.get("best_val_dice"),
        device=model_service.get_device_str(),
        api_version="0.1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/model-info",
    response_model=ModelInfoResponse,
    summary="Trained Model Information and Evaluation Metrics",
    description="Returns architecture, encoder, classes, input resolution, and established benchmark metrics.",
)
async def get_model_info(
    model_service: ModelService = Depends(get_model_service),
) -> ModelInfoResponse:
    """Return model specifications and validated benchmark evaluation metrics."""
    meta = model_service.get_metadata()
    ckpt_path = model_service.checkpoint_path

    return ModelInfoResponse(
        architecture="ResNet34UNet",
        encoder="resnet34",
        supported_classes=["Background (0)", "Oil Spill (1)"],
        input_channels=3,
        input_resolution="256x256 (arbitrary with 32px padding, 512x512 tiled)",
        checkpoint_path=str(ckpt_path),
        checkpoint_epoch=meta.get("epoch", 14),
        checkpoint_best_val_dice=meta.get("best_val_dice", 0.825521353884009),
        device=model_service.get_device_str(),
        evaluation_metrics=EvaluationMetrics(
            precision=0.8776,
            recall=0.8940,
            f1_score=0.8857,
            global_dice=0.8857,
            mean_dice=0.8270,
            global_iou=0.7949,
            mean_iou=0.7327,
        ),
        description=(
            "Trained U-Net with ResNet34 encoder for marine oil spill segmentation on Sentinel-1 SAR imagery."
        ),
    )
