"""
FastAPI router for AIS vessel tracking, live simulator broadcasts, and vessel details.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.simulation.models import VesselAISData
from src.simulation.providers import AISSimulatorProvider

router = APIRouter(prefix="/ais", tags=["AIS Vessel Tracking"])

_ais_provider = AISSimulatorProvider()


@router.get(
    "/vessels",
    response_model=List[VesselAISData],
    summary="Retrieve AIS Vessels",
    description="Retrieve live or simulated vessel positions with optional geographical bounding box filtering.",
)
async def get_vessels(
    min_lat: Optional[float] = Query(None, description="Southern bounding latitude"),
    min_lon: Optional[float] = Query(None, description="Western bounding longitude"),
    max_lat: Optional[float] = Query(None, description="Northern bounding latitude"),
    max_lon: Optional[float] = Query(None, description="Eastern bounding longitude"),
) -> List[VesselAISData]:
    if None not in (min_lat, min_lon, max_lat, max_lon):
        return _ais_provider.search_vessels_in_bbox(min_lat, min_lon, max_lat, max_lon)
    return _ais_provider.get_all_vessels()


@router.get(
    "/vessels/{mmsi}",
    response_model=VesselAISData,
    summary="Get Vessel by MMSI",
    description="Retrieve vessel details and historical AIS trajectory by MMSI.",
)
async def get_vessel_by_mmsi(mmsi: str) -> VesselAISData:
    vessel = _ais_provider.get_vessel_by_mmsi(mmsi)
    if not vessel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vessel with MMSI '{mmsi}' not found.",
        )
    return vessel
