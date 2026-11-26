"""
Pydantic response and request schemas for OceanTrace API.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema for GET /api/health response."""

    status: str = Field(..., description="Overall service status (e.g. 'healthy', 'degraded')")
    model_loaded: bool = Field(..., description="Whether the neural network weights are in memory")
    model_name: str = Field(..., description="Name of the model architecture")
    model_epoch: Optional[int] = Field(None, description="Trained checkpoint epoch number")
    model_best_dice: Optional[float] = Field(None, description="Best validation Dice score recorded")
    device: str = Field(..., description="Active compute device (e.g. 'cpu', 'cuda:0')")
    api_version: str = Field("0.1.0", description="API semantic version")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp of health check")


class GeospatialMetadata(BaseModel):
    """Geospatial metadata for GeoTIFF imagery."""

    is_geotiff: bool = Field(False, description="True if input has georeferencing information")
    crs: Optional[str] = Field(None, description="Coordinate Reference System (e.g. 'EPSG:4326')")
    transform: Optional[List[float]] = Field(None, description="Affine geotransform matrix")
    bounds: Optional[List[float]] = Field(None, description="[left, bottom, right, top] bounding box")
    nodata: Optional[float] = Field(None, description="NoData value if specified")


class PredictionUrls(BaseModel):
    """Relative or absolute URLs to access generated prediction assets."""

    original_image_url: str = Field(..., description="Endpoint to download displayable original image")
    mask_url: str = Field(..., description="Endpoint to download binary spill mask (PNG)")
    overlay_url: str = Field(..., description="Endpoint to download 3-panel visualization overlay")
    details_url: str = Field(..., description="Endpoint to retrieve full JSON prediction result")


class PredictResponse(BaseModel):
    """Schema for POST /api/predict and GET /api/results/{prediction_id}."""

    prediction_id: str = Field(..., description="Unique UUID for this prediction request")
    status: str = Field("completed", description="Status of the inference run ('completed', 'failed')")
    file_name: str = Field(..., description="Original name of the uploaded image file")
    input_dimensions: List[int] = Field(..., description="[height, width] of input in pixels")
    spill_detected: bool = Field(..., description="True if any positive oil spill pixels were detected")
    spill_pixel_count: int = Field(..., description="Total positive spill pixels detected")
    spill_coverage_percentage: float = Field(..., description="Percentage of scene area identified as spill")
    threshold_applied: float = Field(0.5, description="Decision threshold applied to probabilities")
    norm_method: str = Field("percentile", description="Normalization method applied")
    tiled_inference: bool = Field(False, description="True if tiled windowing was used for large imagery")
    inference_time_ms: float = Field(..., description="Forward pass time in milliseconds")
    total_time_ms: float = Field(..., description="Total processing time including I/O in milliseconds")
    prob_min: float = Field(..., description="Minimum probability score in the scene")
    prob_max: float = Field(..., description="Maximum probability score in the scene")
    prob_mean: float = Field(..., description="Mean probability score across all pixels")
    geospatial: GeospatialMetadata = Field(default_factory=GeospatialMetadata, description="CRS and bounds info")
    urls: PredictionUrls = Field(..., description="Direct links to view and download output assets")
    created_at: str = Field(..., description="ISO 8601 UTC timestamp of creation")


class ErrorResponse(BaseModel):
    """Standardized error response schema."""

    error: str = Field(..., description="Short error classification")
    detail: str = Field(..., description="Descriptive error explanation")
    status_code: int = Field(..., description="HTTP status code")
