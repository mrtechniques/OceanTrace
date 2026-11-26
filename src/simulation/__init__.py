"""
OceanTrace Simulation and AIS module initialization.
"""

from src.simulation.correlation import VesselCorrelationEngine
from src.simulation.models import (
    AISTrajectoryPoint,
    CandidateVesselEvidence,
    Sentinel1Scene,
    VesselAISData,
    haversine_distance_km,
    km_to_nm,
)
from src.simulation.providers import AISSimulatorProvider, Sentinel1SimulatorProvider

__all__ = [
    "AISTrajectoryPoint",
    "CandidateVesselEvidence",
    "Sentinel1Scene",
    "VesselAISData",
    "AISSimulatorProvider",
    "Sentinel1SimulatorProvider",
    "VesselCorrelationEngine",
    "haversine_distance_km",
    "km_to_nm",
]
