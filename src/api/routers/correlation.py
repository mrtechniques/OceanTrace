"""
FastAPI router for vessel-to-spill spatial-temporal correlation and attribution.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.simulation.correlation import VesselCorrelationEngine
from src.simulation.models import CandidateVesselEvidence

router = APIRouter(prefix="/correlation", tags=["Vessel Correlation"])

_correlation_engine = VesselCorrelationEngine()


class CorrelateSpillRequest(BaseModel):
    spill_latitude: float = Field(..., ge=-90.0, le=90.0)
    spill_longitude: float = Field(..., ge=-180.0, le=180.0)
    spill_timestamp_utc: str = Field(..., description="ISO 8601 UTC timestamp of spill observation")
    search_radius_km: float = Field(50.0, gt=0.0, le=500.0)
    max_time_diff_hours: float = Field(24.0, gt=0.0, le=168.0)


@router.post(
    "/correlate",
    response_model=List[CandidateVesselEvidence],
    summary="Correlate Vessels with Spill Location",
    description=(
        "Compare detected spill coordinates and observation timestamp against historical AIS vessel tracks. "
        "Returns candidate vessels ranked by proximity, timing, and AIS transmission anomalies. "
        "Provides circumstantial evidence without asserting definitive legal liability."
    ),
)
async def correlate_vessels(req: CorrelateSpillRequest) -> List[CandidateVesselEvidence]:
    return _correlation_engine.correlate_spill(
        spill_lat=req.spill_latitude,
        spill_lon=req.spill_longitude,
        spill_time_utc=req.spill_timestamp_utc,
        search_radius_km=req.search_radius_km,
        max_time_diff_hours=req.max_time_diff_hours,
    )
