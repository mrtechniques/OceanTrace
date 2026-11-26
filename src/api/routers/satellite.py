"""
FastAPI router for Sentinel-1 satellite imagery discovery, catalog search, preview, and download.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from PIL import Image, ImageDraw

from src.api.config import REPO_ROOT
from src.simulation.models import Sentinel1Scene
from src.simulation.providers import Sentinel1SimulatorProvider

router = APIRouter(prefix="/satellite", tags=["Satellite Imagery"])

_storage_dir = REPO_ROOT / "data" / "raw" / "sar"
_satellite_provider = Sentinel1SimulatorProvider(_storage_dir)


def _generate_synthetic_sar_preview(scene: Sentinel1Scene) -> bytes:
    """Generate a realistic synthetic SAR preview chip (256x256)."""
    im = Image.new("L", (256, 256), color=120)
    draw = ImageDraw.Draw(im)
    # Simulate speckled ocean water and dark slick patch
    draw.ellipse([80, 80, 180, 160], fill=35)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


@router.get(
    "/scenes",
    response_model=List[Sentinel1Scene],
    summary="Search Sentinel-1 Satellite Scenes",
    description="Search satellite scenes by geographical bounding box and acquisition date range.",
)
async def search_scenes(
    min_lat: Optional[float] = Query(None, description="Southern bounding latitude"),
    min_lon: Optional[float] = Query(None, description="Western bounding longitude"),
    max_lat: Optional[float] = Query(None, description="Northern bounding latitude"),
    max_lon: Optional[float] = Query(None, description="Eastern bounding longitude"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
) -> List[Sentinel1Scene]:
    return _satellite_provider.search_scenes(
        min_lat=min_lat,
        min_lon=min_lon,
        max_lat=max_lat,
        max_lon=max_lon,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/scenes/{scene_id}",
    response_model=Sentinel1Scene,
    summary="Get Scene Metadata",
    description="Retrieve metadata for a specific Sentinel-1 scene by ID.",
)
async def get_scene_by_id(scene_id: str) -> Sentinel1Scene:
    scene = _satellite_provider.get_scene_by_id(scene_id)
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Satellite scene '{scene_id}' not found.",
        )
    return scene


@router.get(
    "/scenes/{scene_id}/preview",
    summary="Get Scene Preview Image",
    description="Retrieve a 256x256 preview thumbnail for the Sentinel-1 scene.",
)
async def get_scene_preview(scene_id: str):
    scene = _satellite_provider.get_scene_by_id(scene_id)
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Satellite scene '{scene_id}' not found.",
        )
    if scene.file_path and Path(scene.file_path).exists():
        return FileResponse(scene.file_path, media_type="image/png")
    
    # Return synthetic preview
    png_bytes = _generate_synthetic_sar_preview(scene)
    return Response(content=png_bytes, media_type="image/png")


@router.get(
    "/scenes/{scene_id}/download",
    summary="Download Scene Image",
    description="Download the full SAR scene raster file (compatible with /api/predict).",
)
async def download_scene(scene_id: str):
    scene = _satellite_provider.get_scene_by_id(scene_id)
    if not scene:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Satellite scene '{scene_id}' not found.",
        )
    if scene.file_path and Path(scene.file_path).exists():
        return FileResponse(
            scene.file_path,
            media_type="image/png",
            filename=f"{scene_id}.png",
        )
    
    # Fallback to generating a valid SAR scene file on-the-fly and returning it
    target_path = _storage_dir / f"{scene_id}.png"
    if not target_path.exists():
        png_bytes = _generate_synthetic_sar_preview(scene)
        target_path.write_bytes(png_bytes)
        scene.file_path = str(target_path)
    
    return FileResponse(
        str(target_path),
        media_type="image/png",
        filename=f"{scene_id}.png",
    )
