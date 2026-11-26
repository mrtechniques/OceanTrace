"""
Health and status check router for the OceanTrace API.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from src.api.dependencies import ModelService, get_model_service
from src.api.schemas import HealthResponse

router = APIRouter(tags=["Health"])


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
    is_ready = model_service.is_loaded and model_service.model is not None
    meta = model_service.metadata

    return HealthResponse(
        status="healthy" if is_ready else "degraded",
        model_loaded=is_ready,
        model_name="ResNet34UNet",
        model_epoch=meta.get("epoch"),
        model_best_dice=meta.get("best_val_dice"),
        device=model_service.device_str,
        api_version="0.1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
