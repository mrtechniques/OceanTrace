"""
Configuration settings for the OceanTrace FastAPI backend.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Set

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Base storage directories
UPLOAD_DIR = Path(os.getenv("OCEANTRACE_UPLOAD_DIR", str(REPO_ROOT / "data" / "interim" / "uploads")))
RESULTS_DIR = Path(os.getenv("OCEANTRACE_RESULTS_DIR", str(REPO_ROOT / "data" / "processed" / "api_results")))

# Model configuration
DEFAULT_MODEL_PATH = Path(
    os.getenv("OCEANTRACE_MODEL_PATH", str(REPO_ROOT / "models" / "best_oil_spill_unet.pth"))
)
DEFAULT_DEVICE = os.getenv("OCEANTRACE_DEVICE", None)  # None = auto-detect CUDA/CPU

# Inference parameters
DEFAULT_THRESHOLD: float = float(os.getenv("OCEANTRACE_THRESHOLD", "0.5"))
DEFAULT_NORM_METHOD: str = os.getenv("OCEANTRACE_NORM_METHOD", "percentile")
DEFAULT_TILE_SIZE: int = int(os.getenv("OCEANTRACE_TILE_SIZE", "512"))
DEFAULT_OVERLAP: int = int(os.getenv("OCEANTRACE_OVERLAP", "64"))

# Upload constraints
ALLOWED_EXTENSIONS: Set[str] = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".geotiff"}
MAX_UPLOAD_SIZE_MB: int = int(os.getenv("OCEANTRACE_MAX_UPLOAD_SIZE_MB", "100"))

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
