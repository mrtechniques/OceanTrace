"""
Tests for AIS simulator, Sentinel-1 satellite catalog, and spatio-temporal vessel correlation.
"""

from __future__ import annotations

import io
from fastapi.testclient import TestClient
from PIL import Image

from src.api.main import app

client = TestClient(app)


def test_ais_get_all_vessels():
    """Verify GET /api/ais/vessels returns simulated AIS records with required fields."""
    response = client.get("/api/ais/vessels")
    assert response.status_code == 200
    vessels = response.json()
    assert len(vessels) >= 4
    
    # Check required fields on the first vessel
    v = vessels[0]
    assert "mmsi" in v
    assert "vessel_name" in v
    assert "latitude" in v
    assert "longitude" in v
    assert "speed_knots" in v
    assert "heading_deg" in v
    assert "timestamp_utc" in v
    assert "vessel_type" in v
    assert "trajectory" in v
    assert len(v["trajectory"]) > 0


def test_ais_bbox_filtering():
    """Verify bounding box search filters vessels accurately."""
    # Bounding box around Gulf of Oman target area
    response = client.get(
        "/api/ais/vessels?min_lat=24.0&min_lon=56.0&max_lat=26.0&max_lon=59.0"
    )
    assert response.status_code == 200
    vessels = response.json()
    assert len(vessels) > 0
    for v in vessels:
        assert 24.0 <= v["latitude"] <= 26.0
        assert 56.0 <= v["longitude"] <= 59.0

    # Remote bounding box where no simulated vessels operate
    empty_res = client.get(
        "/api/ais/vessels?min_lat=-50.0&min_lon=0.0&max_lat=-40.0&max_lon=10.0"
    )
    assert empty_res.status_code == 200
    assert len(empty_res.json()) == 0


def test_ais_get_single_vessel_by_mmsi():
    """Verify retrieving specific vessel and trajectory by MMSI."""
    response = client.get("/api/ais/vessels/352981000")
    assert response.status_code == 200
    data = response.json()
    assert data["mmsi"] == "352981000"
    assert data["vessel_name"] == "M/T Ocean Crown"
    assert "Dark Window" in data["ais_status"]


def test_ais_get_nonexistent_vessel():
    """Verify 404 response for unknown MMSI."""
    response = client.get("/api/ais/vessels/999999999")
    assert response.status_code == 404


def test_satellite_search_scenes():
    """Verify searching Sentinel-1 satellite scenes."""
    response = client.get("/api/satellite/scenes")
    assert response.status_code == 200
    scenes = response.json()
    assert len(scenes) >= 2
    s = scenes[0]
    assert "scene_id" in s
    assert "bounds" in s
    assert "sensor" in s
    assert "Sentinel-1" in s["sensor"]
    assert s["is_compatible_unet"] is True


def test_satellite_scene_preview_and_download():
    """Verify preview image and raster download endpoints."""
    scene_id = "S1A_IW_GRDH_1SDV_20261125T054211"
    
    # Preview
    preview_res = client.get(f"/api/satellite/scenes/{scene_id}/preview")
    assert preview_res.status_code == 200
    assert preview_res.headers["content-type"].startswith("image/png")

    # Download
    dl_res = client.get(f"/api/satellite/scenes/{scene_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"].startswith("image/png")
    assert len(dl_res.content) > 0


def test_satellite_download_can_be_sent_to_predict():
    """Verify that retrieved Sentinel-1 image is directly compatible with POST /api/predict."""
    scene_id = "S1A_IW_GRDH_1SDV_20261125T054211"
    dl_res = client.get(f"/api/satellite/scenes/{scene_id}/download")
    assert dl_res.status_code == 200
    
    # Send image to existing /api/predict
    files = {"file": ("downloaded_scene.png", io.BytesIO(dl_res.content), "image/png")}
    data = {"threshold": 0.50, "norm_method": "percentile"}
    predict_res = client.post("/api/predict", files=files, data=data)
    
    assert predict_res.status_code == 200
    pred_data = predict_res.json()
    assert pred_data["status"] == "completed"
    assert "spill_detected" in pred_data
    assert "mask_url" in pred_data["urls"]
    assert "overlay_url" in pred_data["urls"]


def test_correlation_engine_ranking():
    """Verify spatial-temporal correlation and candidate ranking."""
    payload = {
        "spill_latitude": 24.812,
        "spill_longitude": 57.240,
        "spill_timestamp_utc": "2026-11-25T05:42:11Z",
        "search_radius_km": 50.0,
        "max_time_diff_hours": 24.0,
    }
    response = client.post("/api/correlation/correlate", json=payload)
    assert response.status_code == 200
    candidates = response.json()
    assert len(candidates) > 0
    
    # Top candidate should be ranked first with highest correlation score
    top = candidates[0]
    assert top["vessel_name"] == "M/T Ocean Crown"
    assert top["mmsi"] == "352981000"
    assert top["correlation_score"] >= 80.0
    assert top["risk_level"] == "High"
    # Ensure evidence summary explicitly mentions circumstantial correlation
    assert "circumstantial correlation" in top["evidence_summary"]


def test_correlation_invalid_coordinates():
    """Verify validation when invalid coordinates are provided."""
    payload = {
        "spill_latitude": 150.0,  # Invalid latitude > 90
        "spill_longitude": 57.240,
        "spill_timestamp_utc": "2026-11-25T05:42:11Z",
    }
    response = client.post("/api/correlation/correlate", json=payload)
    assert response.status_code == 422
