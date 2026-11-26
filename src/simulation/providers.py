"""
Simulated and External Provider implementation for AIS and Sentinel-1 satellite imagery.
Supports configurable offline simulation mode and external live API hooks.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from src.simulation.models import (
    AISTrajectoryPoint,
    CandidateVesselEvidence,
    Sentinel1Scene,
    VesselAISData,
    haversine_distance_km,
    km_to_nm,
)

logger = logging.getLogger(__name__)


class AISSimulatorProvider:
    """
    AIS Data Provider.
    Simulates real-world AIS transponder broadcasts across international shipping lanes
    (Gulf of Oman, Strait of Malacca, Arabian Sea).
    """

    def __init__(self) -> None:
        self._vessels: List[VesselAISData] = self._init_vessel_database()

    def _init_vessel_database(self) -> List[VesselAISData]:
        return [
            VesselAISData(
                mmsi="352981000",
                vessel_name="M/T Ocean Crown",
                imo="9481234",
                callsign="3FYE2",
                flag="Panama 🇵🇦",
                vessel_type="Crude Oil Tanker",
                dwt="158,500 DWT",
                length_m=274.0,
                beam_m=48.0,
                latitude=24.815,
                longitude=57.242,
                speed_knots=5.1,
                heading_deg=132.0,
                timestamp_utc="2026-11-24T19:15:00Z",
                ais_status="Dark Window (118 min Gap)",
                trajectory=[
                    AISTrajectoryPoint(timestamp_utc="2026-11-24T16:00:00Z", latitude=24.450, longitude=56.800, speed_knots=14.2, heading_deg=128.0, ais_active=True),
                    AISTrajectoryPoint(timestamp_utc="2026-11-24T18:40:00Z", latitude=24.620, longitude=57.020, speed_knots=13.8, heading_deg=130.0, ais_active=False),
                    AISTrajectoryPoint(timestamp_utc="2026-11-24T19:15:00Z", latitude=24.645, longitude=57.050, speed_knots=5.1, heading_deg=132.0, ais_active=False),
                    AISTrajectoryPoint(timestamp_utc="2026-11-24T20:38:00Z", latitude=24.710, longitude=57.125, speed_knots=13.9, heading_deg=131.0, ais_active=True),
                    AISTrajectoryPoint(timestamp_utc="2026-11-25T05:42:00Z", latitude=24.815, longitude=57.242, speed_knots=14.0, heading_deg=135.0, ais_active=True),
                ],
            ),
            VesselAISData(
                mmsi="563045000",
                vessel_name="Pacific Voyager",
                imo="9324567",
                callsign="9V8921",
                flag="Singapore 🇸🇬",
                vessel_type="Container Ship",
                dwt="68,200 DWT",
                length_m=294.0,
                beam_m=32.0,
                latitude=24.870,
                longitude=57.310,
                speed_knots=19.4,
                heading_deg=310.0,
                timestamp_utc="2026-11-24T20:45:00Z",
                ais_status="Continuous Broadcast",
                trajectory=[
                    AISTrajectoryPoint(timestamp_utc="2026-11-24T18:00:00Z", latitude=24.510, longitude=57.650, speed_knots=19.5, heading_deg=310.0, ais_active=True),
                    AISTrajectoryPoint(timestamp_utc="2026-11-24T20:45:00Z", latitude=24.750, longitude=57.380, speed_knots=19.4, heading_deg=310.0, ais_active=True),
                    AISTrajectoryPoint(timestamp_utc="2026-11-25T05:42:00Z", latitude=25.200, longitude=56.900, speed_knots=19.2, heading_deg=312.0, ais_active=True),
                ],
            ),
            VesselAISData(
                mmsi="636015000",
                vessel_name="Blue Marlin",
                imo="9192837",
                callsign="A8LK3",
                flag="Liberia 🇱🇷",
                vessel_type="Bulk Carrier",
                dwt="82,100 DWT",
                length_m=229.0,
                beam_m=32.0,
                latitude=24.950,
                longitude=57.350,
                speed_knots=11.8,
                heading_deg=125.0,
                timestamp_utc="2026-11-24T17:30:00Z",
                ais_status="Continuous Broadcast",
                trajectory=[
                    AISTrajectoryPoint(timestamp_utc="2026-11-24T15:00:00Z", latitude=25.100, longitude=57.100, speed_knots=11.8, heading_deg=125.0, ais_active=True),
                    AISTrajectoryPoint(timestamp_utc="2026-11-24T17:30:00Z", latitude=24.950, longitude=57.350, speed_knots=11.8, heading_deg=125.0, ais_active=True),
                    AISTrajectoryPoint(timestamp_utc="2026-11-25T05:42:00Z", latitude=24.150, longitude=58.200, speed_knots=12.0, heading_deg=125.0, ais_active=True),
                ],
            ),
            VesselAISData(
                mmsi="403567000",
                vessel_name="Al-Sabah Star",
                imo="9554321",
                callsign="HZZ8",
                flag="Saudi Arabia 🇸🇦",
                vessel_type="Chemical Tanker",
                dwt="49,990 DWT",
                length_m=183.0,
                beam_m=32.0,
                latitude=24.980,
                longitude=57.450,
                speed_knots=13.5,
                heading_deg=305.0,
                timestamp_utc="2026-11-24T22:10:00Z",
                ais_status="Continuous Broadcast",
                trajectory=[
                    AISTrajectoryPoint(timestamp_utc="2026-11-24T20:00:00Z", latitude=24.700, longitude=57.800, speed_knots=13.5, heading_deg=305.0, ais_active=True),
                    AISTrajectoryPoint(timestamp_utc="2026-11-24T22:10:00Z", latitude=24.980, longitude=57.450, speed_knots=13.5, heading_deg=305.0, ais_active=True),
                    AISTrajectoryPoint(timestamp_utc="2026-11-25T05:42:00Z", latitude=25.400, longitude=56.950, speed_knots=13.4, heading_deg=305.0, ais_active=True),
                ],
            ),
        ]

    def get_all_vessels(self) -> List[VesselAISData]:
        return self._vessels

    def get_vessel_by_mmsi(self, mmsi: str) -> Optional[VesselAISData]:
        for v in self._vessels:
            if v.mmsi == mmsi:
                return v
        return None

    def search_vessels_in_bbox(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
    ) -> List[VesselAISData]:
        results = []
        for v in self._vessels:
            if min_lat <= v.latitude <= max_lat and min_lon <= v.longitude <= max_lon:
                results.append(v)
        return results


class Sentinel1SimulatorProvider:
    """
    Sentinel-1 Satellite Imagery Provider.
    Simulates ESA Copernicus Open Access Hub / CDSE data retrieval and catalog search.
    Provides sample scenes compatible with our ResNet34 U-Net pipeline.
    """

    def __init__(self, sample_storage_dir: Path) -> None:
        self.storage_dir = sample_storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._scenes: List[Sentinel1Scene] = self._init_scene_catalog()

    def _init_scene_catalog(self) -> List[Sentinel1Scene]:
        sample_png = self.storage_dir / "synthetic_sar_sample.png"
        return [
            Sentinel1Scene(
                scene_id="S1A_IW_GRDH_1SDV_20261125T054211",
                scene_name="Gulf of Oman (Major Shipping Corridor)",
                sensor="Sentinel-1A IW GRD",
                mode="Interferometric Wide Swath (IW)",
                polarization="VV + VH",
                resolution="10 m / pixel",
                orbit="142 (Descending)",
                pass_direction="Descending",
                acquisition_utc="2026-11-25T05:42:11Z",
                bounds=[[24.2, 56.4], [25.4, 58.1]],
                center=[24.812, 57.240],
                file_path=str(sample_png) if sample_png.exists() else None,
                preview_url="/api/satellite/scenes/S1A_IW_GRDH_1SDV_20261125T054211/preview",
                download_url="/api/satellite/scenes/S1A_IW_GRDH_1SDV_20261125T054211/download",
                cloud_coverage_pct=0.0,
                is_compatible_unet=True,
            ),
            Sentinel1Scene(
                scene_id="S1B_IW_GRDH_1SDV_20261124T181903",
                scene_name="Strait of Malacca (Deepwater Channel)",
                sensor="Sentinel-1B IW GRD",
                mode="Interferometric Wide Swath (IW)",
                polarization="VV + VH",
                resolution="10 m / pixel",
                orbit="089 (Ascending)",
                pass_direction="Ascending",
                acquisition_utc="2026-11-24T18:19:03Z",
                bounds=[[1.6, 101.4], [2.7, 103.0]],
                center=[2.148, 102.189],
                file_path=str(sample_png) if sample_png.exists() else None,
                preview_url="/api/satellite/scenes/S1B_IW_GRDH_1SDV_20261124T181903/preview",
                download_url="/api/satellite/scenes/S1B_IW_GRDH_1SDV_20261124T181903/download",
                cloud_coverage_pct=0.0,
                is_compatible_unet=True,
            ),
        ]

    def search_scenes(
        self,
        min_lat: Optional[float] = None,
        min_lon: Optional[float] = None,
        max_lat: Optional[float] = None,
        max_lon: Optional[float] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Sentinel1Scene]:
        results = []
        for s in self._scenes:
            # Check bounding box intersection if provided
            if min_lat is not None and max_lat is not None:
                scene_min_lat = s.bounds[0][0]
                scene_max_lat = s.bounds[1][0]
                scene_min_lon = s.bounds[0][1]
                scene_max_lon = s.bounds[1][1]
                if (scene_max_lat < min_lat or scene_min_lat > max_lat or
                    scene_max_lon < min_lon or scene_min_lon > max_lon):
                    continue
            results.append(s)
        return results

    def get_scene_by_id(self, scene_id: str) -> Optional[Sentinel1Scene]:
        for s in self._scenes:
            if s.scene_id == scene_id:
                return s
        return None
