"""
API integration tests for the OceanTrace FastAPI endpoints.
"""

import io
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from fastapi.testclient import TestClient
from PIL import Image

from src.api.main import app

client = TestClient(app)


@pytest.fixture
def sample_png_bytes() -> io.BytesIO:
    """Generate an in-memory PNG image with a synthetic dark oil patch."""
    arr = np.random.randint(50, 200, size=(128, 128), dtype=np.uint8)
    arr[30:70, 30:70] = 10  # Low backscatter patch
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    buf.seek(0)
    return buf


@pytest.fixture
def sample_geotiff_bytes() -> io.BytesIO:
    """Generate an in-memory GeoTIFF file with CRS and geotransform."""
    width, height = 128, 128
    transform = from_origin(10.0, 50.0, 10.0, 10.0)
    data = np.random.uniform(0.02, 0.2, size=(1, height, width)).astype(np.float32)
    data[0, 20:60, 20:60] = 0.005  # Synthetic spill

    with MemoryFile() as memfile:
        with memfile.open(
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype=data.dtype,
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            dst.write(data)
        return io.BytesIO(memfile.read())


def test_health_endpoint():
    """Verify GET /api/health reports system status, model epoch, and device."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert data["model_name"] == "ResNet34UNet"
    assert data["model_epoch"] == 14
    assert pytest.approx(data["model_best_dice"], rel=1e-4) == 0.8255
    assert "device" in data
    assert "timestamp" in data


def test_model_info_endpoint():
    """Verify GET /api/model-info returns architecture, classes, and established evaluation metrics."""
    response = client.get("/api/model-info")
    assert response.status_code == 200
    data = response.json()

    assert data["architecture"] == "ResNet34UNet"
    assert data["encoder"] == "resnet34"
    assert data["input_channels"] == 3
    assert "Background (0)" in data["supported_classes"][0]
    assert "Oil Spill (1)" in data["supported_classes"][1]
    assert data["checkpoint_epoch"] == 14
    assert pytest.approx(data["checkpoint_best_val_dice"], rel=1e-4) == 0.8255

    # Verify established evaluation metrics
    metrics = data["evaluation_metrics"]
    assert pytest.approx(metrics["precision"], rel=1e-4) == 0.8776
    assert pytest.approx(metrics["recall"], rel=1e-4) == 0.8940
    assert pytest.approx(metrics["f1_score"], rel=1e-4) == 0.8857
    assert pytest.approx(metrics["global_dice"], rel=1e-4) == 0.8857
    assert pytest.approx(metrics["mean_dice"], rel=1e-4) == 0.8270
    assert pytest.approx(metrics["global_iou"], rel=1e-4) == 0.7949
    assert pytest.approx(metrics["mean_iou"], rel=1e-4) == 0.7327



def test_predict_png_and_retrieve_results(sample_png_bytes: io.BytesIO):
    """Verify POST /api/predict with PNG upload and subsequent asset retrieval."""
    response = client.post(
        "/api/predict",
        files={"file": ("sar_scene.png", sample_png_bytes, "image/png")},
        data={"threshold": 0.5, "norm_method": "percentile"},
    )
    assert response.status_code == 200
    data = response.json()

    prediction_id = data["prediction_id"]
    assert prediction_id is not None
    assert data["status"] == "completed"
    assert data["file_name"] == "sar_scene.png"
    assert data["input_dimensions"] == [128, 128]
    assert isinstance(data["spill_detected"], bool)
    assert isinstance(data["spill_pixel_count"], int)
    assert "inference_time_ms" in data
    assert "urls" in data

    urls = data["urls"]
    assert urls["mask_url"] == f"/api/results/{prediction_id}/mask"
    assert urls["overlay_url"] == f"/api/results/{prediction_id}/overlay"
    assert urls["original_image_url"] == f"/api/results/{prediction_id}/original"
    assert urls["details_url"] == f"/api/results/{prediction_id}"
    assert data["mask_url"] == urls["mask_url"]
    assert data["overlay_url"] == urls["overlay_url"]
    assert data["original_image_url"] == urls["original_image_url"]
    assert "processing_time_ms" in data

    # 1. Retrieve full details via GET /api/results/{prediction_id}
    res_details = client.get(f"/api/results/{prediction_id}")
    assert res_details.status_code == 200
    assert res_details.json()["prediction_id"] == prediction_id

    # 2. Retrieve original image
    res_orig = client.get(urls["original_image_url"])
    assert res_orig.status_code == 200
    assert res_orig.headers["content-type"] == "image/png"

    # 3. Retrieve binary mask
    res_mask = client.get(urls["mask_url"])
    assert res_mask.status_code == 200
    assert res_mask.headers["content-type"] == "image/png"

    # 4. Retrieve 3-panel overlay
    res_overlay = client.get(urls["overlay_url"])
    assert res_overlay.status_code == 200
    assert res_overlay.headers["content-type"] == "image/png"


def test_predict_geotiff_preserves_metadata(sample_geotiff_bytes: io.BytesIO):
    """Verify POST /api/predict on GeoTIFF retains CRS and transform info."""
    response = client.post(
        "/api/predict",
        files={"file": ("sentinel1_slice.tif", sample_geotiff_bytes, "image/tiff")},
        data={"threshold": 0.45, "norm_method": "percentile"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "completed"
    geo = data["geospatial"]
    assert geo["is_geotiff"] is True
    assert geo["crs"] == "EPSG:4326"
    assert geo["transform"] is not None
    assert geo["bounds"] is not None


def test_predict_invalid_extension():
    """Verify 400 rejection for unsupported file extensions."""
    fake_file = io.BytesIO(b"dummy text file content")
    response = client.post(
        "/api/predict",
        files={"file": ("malicious_or_invalid.exe", fake_file, "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_predict_invalid_threshold(sample_png_bytes: io.BytesIO):
    """Verify 400 rejection for out-of-bounds threshold parameter."""
    response = client.post(
        "/api/predict",
        files={"file": ("sample.png", sample_png_bytes, "image/png")},
        data={"threshold": 1.75},  # Invalid: must be <= 1.0
    )
    assert response.status_code == 400
    assert "Threshold must be between 0.0 and 1.0" in response.json()["detail"]


def test_results_not_found():
    """Verify 404 response when querying non-existent prediction IDs."""
    response = client.get("/api/results/non_existent_id_abc123")
    assert response.status_code == 404
    assert "was not found" in response.json()["detail"]
