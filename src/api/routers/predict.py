"""
Inference and results retrieval routers for the OceanTrace API.
"""

from __future__ import annotations

import json
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image

from src.api.config import (
    ALLOWED_EXTENSIONS,
    DEFAULT_NORM_METHOD,
    DEFAULT_OVERLAP,
    DEFAULT_THRESHOLD,
    DEFAULT_TILE_SIZE,
    MAX_UPLOAD_SIZE_MB,
    RESULTS_DIR,
    UPLOAD_DIR,
)
from src.api.dependencies import ModelManager, get_model_manager
from src.api.schemas import GeospatialMetadata, PredictionUrls, PredictResponse
from src.detection.segmentation.predict import predict_oil_spill
from src.detection.utils.visualization import (
    create_prediction_figure,
    save_prediction_visualization,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Inference"])


def _build_urls(prediction_id: str) -> PredictionUrls:
    """Generate canonical endpoint URLs for prediction assets."""
    return PredictionUrls(
        original_image_url=f"/api/results/{prediction_id}/original",
        mask_url=f"/api/results/{prediction_id}/mask",
        overlay_url=f"/api/results/{prediction_id}/overlay",
        details_url=f"/api/results/{prediction_id}",
    )


@router.post(
    "/predict",
    response_model=PredictResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Oil Spill Segmentation",
    description="Upload a satellite SAR scene or optical image (PNG, JPG, GeoTIFF) for neural network inference.",
)
async def predict_spill_endpoint(
    file: UploadFile = File(..., description="Image file (PNG, JPG, JPEG, GeoTIFF)"),
    threshold: float = Form(DEFAULT_THRESHOLD, description="Confidence threshold [0.0 - 1.0]"),
    norm_method: str = Form(DEFAULT_NORM_METHOD, description="Normalization method ('percentile', 'minmax', 'imagenet', 'zscore', 'none')"),
    tile_size: int = Form(DEFAULT_TILE_SIZE, description="Tile patch size for large satellite imagery"),
    overlap: int = Form(DEFAULT_OVERLAP, description="Tile overlap in pixels for seamless boundary blending"),
    manager: ModelManager = Depends(get_model_manager),
) -> PredictResponse:
    """Accept an uploaded image, run ResNet34 U-Net inference, and persist prediction assets."""
    filename = file.filename or "uploaded_image.png"
    suffix = Path(filename).suffix.lower()

    # 1. Validate file format
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file format '{suffix}'. "
                f"Allowed formats are: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    # 2. Validate threshold bounds
    if not (0.0 <= threshold <= 1.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Threshold must be between 0.0 and 1.0; received {threshold}",
        )

    prediction_id = uuid.uuid4().hex
    upload_path = UPLOAD_DIR / f"{prediction_id}_{filename}"
    pred_dir = RESULTS_DIR / prediction_id
    pred_dir.mkdir(parents=True, exist_ok=True)

    # 3. Stream upload to disk while enforcing max file size
    bytes_read = 0
    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    try:
        with open(upload_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                bytes_read += len(chunk)
                if bytes_read > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum upload size of {MAX_UPLOAD_SIZE_MB}MB",
                    )
                buffer.write(chunk)
    except Exception as exc:
        if upload_path.exists():
            upload_path.unlink()
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {str(exc)}",
        )

    # 4. Run inference using pre-loaded model
    try:
        model = manager.get_model()
        res = predict_oil_spill(
            image_input=upload_path,
            model=model,
            threshold=threshold,
            norm_method=norm_method,
            tile_size=tile_size,
            overlap=overlap,
        )
    except Exception as exc:
        logger.exception("Inference failed for upload %s", filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference pipeline execution error: {str(exc)}",
        )

    # 5. Persist prediction artifacts to disk
    original_path = pred_dir / "original.png"
    mask_path = pred_dir / "mask.png"
    overlay_path = pred_dir / "overlay.png"
    details_path = pred_dir / "results.json"

    # Save original display image
    Image.fromarray(res.original_image).save(original_path)

    # Save binary segmentation mask (0 / 255 PNG)
    Image.fromarray((res.binary_mask * 255).astype("uint8")).save(mask_path)

    # Save 3-panel detection overlay visualization
    fig = create_prediction_figure(
        original_image=res.original_image,
        probability_map=res.probability_map,
        binary_mask=res.binary_mask,
        metadata=res.metadata,
    )
    save_prediction_visualization(fig, overlay_path)

    # Extract geospatial metadata if present
    geo_meta = GeospatialMetadata(
        is_geotiff=bool(res.metadata.get("is_geotiff", False)),
        crs=res.metadata.get("crs"),
        transform=res.metadata.get("transform"),
        bounds=res.metadata.get("bounds"),
        nodata=res.metadata.get("nodata"),
    )

    created_iso = datetime.now(timezone.utc).isoformat()
    urls = _build_urls(prediction_id)

    response = PredictResponse(
        prediction_id=prediction_id,
        status="completed",
        file_name=filename,
        input_dimensions=list(res.metadata.get("input_dimensions", [0, 0])),
        spill_detected=res.spill_detected,
        spill_pixel_count=res.spill_pixel_count,
        spill_coverage_percentage=res.metadata.get("spill_coverage_percentage", 0.0),
        threshold_applied=threshold,
        norm_method=norm_method,
        tiled_inference=bool(res.metadata.get("tiled_inference", False)),
        inference_time_ms=res.metadata.get("inference_time_ms", 0.0),
        total_time_ms=res.metadata.get("total_time_ms", 0.0),
        prob_min=res.metadata.get("prob_min", 0.0),
        prob_max=res.metadata.get("prob_max", 0.0),
        prob_mean=res.metadata.get("prob_mean", 0.0),
        geospatial=geo_meta,
        urls=urls,
        created_at=created_iso,
    )

    # Save complete JSON result
    with open(details_path, "w", encoding="utf-8") as f:
        f.write(response.model_dump_json(indent=2))

    return response


@router.get(
    "/results/{prediction_id}",
    response_model=PredictResponse,
    summary="Retrieve Prediction Metadata",
    description="Retrieve the complete prediction metadata and summary metrics for a past inference task.",
)
def get_prediction_result(prediction_id: str) -> PredictResponse:
    """Load and return serialized prediction metadata by ID."""
    details_path = RESULTS_DIR / prediction_id / "results.json"
    if not details_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prediction result '{prediction_id}' was not found.",
        )

    try:
        with open(details_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return PredictResponse(**data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read result data: {str(exc)}",
        )


@router.get(
    "/results/{prediction_id}/original",
    summary="Get Displayable Original Image",
    response_class=FileResponse,
)
def get_original_image(prediction_id: str) -> FileResponse:
    """Download or display the original uploaded image."""
    file_path = RESULTS_DIR / prediction_id / "original.png"
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original image not found.")
    return FileResponse(file_path, media_type="image/png")


@router.get(
    "/results/{prediction_id}/mask",
    summary="Get Binary Spill Mask",
    response_class=FileResponse,
)
def get_binary_mask(prediction_id: str) -> FileResponse:
    """Download the predicted binary oil spill mask as a PNG."""
    file_path = RESULTS_DIR / prediction_id / "mask.png"
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Spill mask not found.")
    return FileResponse(file_path, media_type="image/png")


@router.get(
    "/results/{prediction_id}/overlay",
    summary="Get 3-Panel Overlay Visualization",
    response_class=FileResponse,
)
def get_overlay_image(prediction_id: str) -> FileResponse:
    """Download the 3-panel visualization figure."""
    file_path = RESULTS_DIR / prediction_id / "overlay.png"
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Overlay visualization not found.")
    return FileResponse(file_path, media_type="image/png")
