"""
OceanTrace Simulation & External Data Provider Module.
Provides realistic maritime AIS simulation, Sentinel-1 satellite scene catalog/search,
and spatio-temporal vessel correlation services.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two GPS coordinates in kilometers."""
    r = 6371.0  # Earth's mean radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def km_to_nm(km: float) -> float:
    """Convert kilometers to nautical miles."""
    return km / 1.852


class AISTrajectoryPoint(BaseModel):
    timestamp_utc: str
    latitude: float
    longitude: float
    speed_knots: float
    heading_deg: float
    ais_active: bool = True


class VesselAISData(BaseModel):
    mmsi: str = Field(..., description="Maritime Mobile Service Identity (9-digit identifier)")
    vessel_name: str = Field(..., description="Registered vessel name")
    imo: Optional[str] = None
    callsign: Optional[str] = None
    flag: str = "Unknown"
    vessel_type: str = Field(..., description="Vessel classification (e.g. Tanker, Cargo, Container)")
    dwt: Optional[str] = None
    length_m: Optional[float] = None
    beam_m: Optional[float] = None
    latitude: float = Field(..., description="Current/latest known latitude")
    longitude: float = Field(..., description="Current/latest known longitude")
    speed_knots: float = Field(..., description="Speed over ground (knots)")
    heading_deg: float = Field(..., description="Course over ground / heading (degrees)")
    timestamp_utc: str = Field(..., description="ISO 8601 UTC timestamp")
    ais_status: str = Field(..., description="Broadcast status: 'Continuous Broadcast' or 'Dark Window'")
    trajectory: List[AISTrajectoryPoint] = Field(default_factory=list, description="Historical track waypoints")


class Sentinel1Scene(BaseModel):
    scene_id: str
    scene_name: str
    sensor: str = "Sentinel-1A IW GRD"
    mode: str = "Interferometric Wide Swath (IW)"
    polarization: str = "VV + VH"
    resolution: str = "10 m / pixel"
    orbit: str
    pass_direction: str  # "Ascending" or "Descending"
    acquisition_utc: str
    bounds: List[List[float]] = Field(..., description="Bounding box [[min_lat, min_lon], [max_lat, max_lon]]")
    center: List[float] = Field(..., description="[lat, lon] center coordinate")
    file_path: Optional[str] = None
    preview_url: Optional[str] = None
    download_url: Optional[str] = None
    cloud_coverage_pct: float = 0.0  # SAR penetrates clouds
    is_compatible_unet: bool = True


class CandidateVesselEvidence(BaseModel):
    mmsi: str
    vessel_name: str
    vessel_type: str
    flag: str
    cpa_distance_km: float
    cpa_distance_nm: float
    cpa_timestamp_utc: str
    time_difference_hours: float
    speed_profile: str
    ais_status: str
    ais_gap_details: Optional[str] = None
    correlation_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: str = "Low"  # "Low", "Medium", "High"
    evidence_summary: str
    is_culprit: bool = False
