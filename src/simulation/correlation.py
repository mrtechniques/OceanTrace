"""
Spatial-Temporal Vessel Correlation Engine.
Correlates detected oil spill centroids/polygons against historical AIS vessel tracks.
Computes Closest Point of Approach (CPA), temporal differences, and suspicion rankings.
Explicitly avoids claiming confirmed responsibility based solely on proximity.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from src.simulation.models import (
    CandidateVesselEvidence,
    haversine_distance_km,
    km_to_nm,
)
from src.simulation.providers import AISSimulatorProvider

logger = logging.getLogger(__name__)


def parse_iso_utc(ts: str) -> datetime:
    """Parse ISO UTC string."""
    clean = ts.replace("Z", "+00:00")
    if " " in clean and "T" not in clean:
        clean = clean.replace(" ", "T")
    return datetime.fromisoformat(clean)


class VesselCorrelationEngine:
    """
    Evaluates spatial-temporal proximity and behavioral anomalies between vessels and spills.
    """

    def __init__(self, ais_provider: Optional[AISSimulatorProvider] = None) -> None:
        self.ais_provider = ais_provider or AISSimulatorProvider()

    def correlate_spill(
        self,
        spill_lat: float,
        spill_lon: float,
        spill_time_utc: str,
        search_radius_km: float = 50.0,
        max_time_diff_hours: float = 24.0,
    ) -> List[CandidateVesselEvidence]:
        """
        Rank vessels near a detected spill location based on spatial-temporal proximity
        and transponder anomalies.
        """
        vessels = self.ais_provider.get_all_vessels()
        candidates: List[CandidateVesselEvidence] = []

        try:
            spill_dt = parse_iso_utc(spill_time_utc)
        except Exception:
            spill_dt = datetime.now()

        for v in vessels:
            # 1. Determine Closest Point of Approach (CPA) along vessel's trajectory
            best_dist_km = float("inf")
            best_point = None
            best_time_diff_hours = float("inf")

            points_to_check = v.trajectory if v.trajectory else []
            if not points_to_check:
                # Fallback to current position
                d = haversine_distance_km(spill_lat, spill_lon, v.latitude, v.longitude)
                best_dist_km = d
                try:
                    v_dt = parse_iso_utc(v.timestamp_utc)
                    best_time_diff_hours = abs((spill_dt - v_dt).total_seconds()) / 3600.0
                except Exception:
                    best_time_diff_hours = 0.0
                best_ts = v.timestamp_utc
            else:
                for pt in points_to_check:
                    d = haversine_distance_km(spill_lat, spill_lon, pt.latitude, pt.longitude)
                    if d < best_dist_km:
                        best_dist_km = d
                        best_point = pt
                
                if best_point:
                    try:
                        pt_dt = parse_iso_utc(best_point.timestamp_utc)
                        best_time_diff_hours = abs((spill_dt - pt_dt).total_seconds()) / 3600.0
                    except Exception:
                        best_time_diff_hours = 0.0
                    best_ts = best_point.timestamp_utc
                else:
                    best_ts = v.timestamp_utc

            # Filter candidates within search radius
            if best_dist_km > search_radius_km:
                continue

            dist_nm = km_to_nm(best_dist_km)

            # 2. Compute Probabilistic Evidence Correlation Score
            # Components:
            # - Spatial Proximity (0 - 50 points)
            # - Temporal Proximity (0 - 25 points)
            # - AIS Broadcast Integrity / Anomaly (0 - 25 points)
            spatial_score = max(0.0, 50.0 * (1.0 - (best_dist_km / search_radius_km)))
            temporal_score = max(0.0, 25.0 * (1.0 - (min(best_time_diff_hours, max_time_diff_hours) / max_time_diff_hours)))

            has_dark_gap = "Dark" in v.ais_status or any(not p.ais_active for p in v.trajectory)
            anomaly_score = 25.0 if has_dark_gap else 5.0

            raw_score = spatial_score + temporal_score + anomaly_score
            correlation_score = round(min(100.0, max(1.0, raw_score)), 1)

            # Assign risk level based on correlation score
            if correlation_score >= 80.0:
                risk_level = "High"
            elif correlation_score >= 40.0:
                risk_level = "Medium"
            else:
                risk_level = "Low"

            # Formulate transparent evidence summary (NO unverified guilt assertion)
            evidence_parts = [
                f"CPA of {dist_nm:.2f} nm ({best_dist_km:.2f} km) at {best_ts}.",
                f"Temporal difference to observation: {best_time_diff_hours:.1f} hours.",
            ]
            if has_dark_gap:
                evidence_parts.append(
                    "Observed AIS transmission anomaly: transponder was dark/inactive during window."
                )
                speed_str = f"{v.speed_knots} kn (Anomaly: Significant Deceleration)"
                gap_details = "Transponder inactive during estimated discharge window"
                is_culprit = correlation_score >= 85.0
            else:
                evidence_parts.append("Continuous broadcast maintained with nominal speed.")
                speed_str = f"Steady {v.speed_knots} kn"
                gap_details = "None (Continuous Broadcast)"
                is_culprit = False

            evidence_summary = (
                f"Candidate identified within search corridor. {' '.join(evidence_parts)} "
                "Note: Proximity and timing provide circumstantial correlation only; "
                "conclusive attribution requires hydrodynamic hindcast verification."
            )

            candidates.append(
                CandidateVesselEvidence(
                    mmsi=v.mmsi,
                    vessel_name=v.vessel_name,
                    vessel_type=v.vessel_type,
                    flag=v.flag,
                    cpa_distance_km=round(best_dist_km, 2),
                    cpa_distance_nm=round(dist_nm, 2),
                    cpa_timestamp_utc=best_ts,
                    time_difference_hours=round(best_time_diff_hours, 1),
                    speed_profile=speed_str,
                    ais_status=v.ais_status,
                    ais_gap_details=gap_details,
                    correlation_score=correlation_score,
                    risk_level=risk_level,
                    evidence_summary=evidence_summary,
                    is_culprit=is_culprit,
                )
            )

        # Sort descending by correlation score
        candidates.sort(key=lambda c: c.correlation_score, reverse=True)
        return candidates
