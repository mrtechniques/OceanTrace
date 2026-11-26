"""
Comprehensive tests for the OceanTrace inference pipeline, image loaders,
preprocessing, tiled prediction, and visualization.
"""

from pathlib import Path

import numpy as np
import pytest
import rasterio
import torch
from rasterio.transform import from_origin
from PIL import Image

from src.detection.preprocessing.loader import convert_to_three_channel, load_image
from src.detection.preprocessing.normalization import normalize_image
from src.detection.segmentation.model import load_oil_spill_model
from src.detection.segmentation.predict import (
    PredictionResult,
    predict_oil_spill,
    predict_patch_direct,
    predict_tiled,
)
from src.detection.utils.visualization import (
    create_overlay,
    create_prediction_figure,
    save_prediction_visualization,
)

CHECKPOINT_PATH = Path("models/best_oil_spill_unet.pth")


@pytest.fixture
def sample_png_path(tmp_path: Path) -> Path:
    """Create a temporary PNG image for testing."""
    file_path = tmp_path / "test_sar.png"
    arr = np.random.randint(0, 255, size=(256, 256), dtype=np.uint8)
    # Inject a dark oil spill patch
    arr[60:140, 60:140] = 10
    Image.fromarray(arr).save(file_path)
    return file_path


@pytest.fixture
def sample_jpg_path(tmp_path: Path) -> Path:
    """Create a temporary JPG image for testing."""
    file_path = tmp_path / "test_optical.jpg"
    arr = np.random.randint(0, 255, size=(256, 256, 3), dtype=np.uint8)
    Image.fromarray(arr).save(file_path, quality=95)
    return file_path


@pytest.fixture
def sample_geotiff_path(tmp_path: Path) -> Path:
    """Create a temporary GeoTIFF raster with valid CRS and transform."""
    file_path = tmp_path / "test_sentinel1.tif"
    width, height = 300, 300
    transform = from_origin(10.0, 50.0, 10.0, 10.0)  # 10m pixel size
    crs = "EPSG:4326"

    # Synthetic SAR backscatter (linear scale)
    data = np.random.uniform(0.01, 0.25, size=(1, height, width)).astype(np.float32)
    # Inject synthetic spill
    data[0, 50:120, 50:120] = 0.002

    with rasterio.open(
        file_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=data.dtype,
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(data)

    return file_path


def test_load_png(sample_png_path: Path):
    """Verify PNG loading and metadata extraction."""
    img, meta = load_image(sample_png_path)
    assert isinstance(img, np.ndarray)
    assert img.shape == (256, 256)
    assert meta["format"] == "png"
    assert meta["width"] == 256
    assert meta["height"] == 256
    assert meta["is_geotiff"] is False


def test_load_jpg(sample_jpg_path: Path):
    """Verify JPG loading and metadata extraction."""
    img, meta = load_image(sample_jpg_path)
    assert isinstance(img, np.ndarray)
    assert img.shape == (256, 256, 3)
    assert meta["format"] in ("jpg", "jpeg")
    assert meta["channels"] == 3


def test_load_geotiff(sample_geotiff_path: Path):
    """Verify GeoTIFF loading, CRS extraction, and transform recovery."""
    img, meta = load_image(sample_geotiff_path)
    assert isinstance(img, np.ndarray)
    assert img.shape == (300, 300)
    assert meta["is_geotiff"] is True
    assert meta["crs"] == "EPSG:4326"
    assert meta["transform"] is not None
    assert meta["bounds"] is not None


def test_convert_to_three_channel():
    """Verify 3-channel conversion across various input shapes."""
    # 2D (H, W) -> (H, W, 3)
    arr_2d = np.ones((64, 64), dtype=np.float32) * 5.0
    out_2d = convert_to_three_channel(arr_2d, mode="repeat")
    assert out_2d.shape == (64, 64, 3)
    assert np.all(out_2d[:, :, 0] == out_2d[:, :, 1])

    # 3D with 1 channel (H, W, 1) -> (H, W, 3)
    arr_3d_1 = np.ones((64, 64, 1), dtype=np.float32)
    out_3d_1 = convert_to_three_channel(arr_3d_1)
    assert out_3d_1.shape == (64, 64, 3)

    # 4-channel RGBA (H, W, 4) -> (H, W, 3) (drop alpha)
    arr_4ch = np.zeros((64, 64, 4), dtype=np.uint8)
    arr_4ch[:, :, 0] = 100
    out_4ch = convert_to_three_channel(arr_4ch)
    assert out_4ch.shape == (64, 64, 3)
    assert out_4ch[0, 0, 0] == 100

    # Zeros mode
    out_zeros = convert_to_three_channel(arr_2d, mode="zeros")
    assert np.all(out_zeros[:, :, 1] == 0)
    assert np.all(out_zeros[:, :, 2] == 0)


def test_normalization_schemes():
    """Verify all configurable normalization methods output finite floats."""
    arr = np.linspace(10, 200, num=1000).reshape(10, 10, 10).astype(np.float32)

    # 1. Percentile
    norm_p = normalize_image(arr, method="percentile", percentile_range=(5, 95))
    assert norm_p.dtype == np.float32
    assert np.all(norm_p >= 0.0) and np.all(norm_p <= 1.0)

    # 2. MinMax
    norm_mm = normalize_image(arr, method="minmax")
    assert norm_mm.dtype == np.float32
    assert np.isclose(norm_mm.min(), 0.0) and np.isclose(norm_mm.max(), 1.0)

    # 3. ImageNet
    arr_3ch = np.random.uniform(0, 1, size=(32, 32, 3)).astype(np.float32)
    norm_in = normalize_image(arr_3ch, method="imagenet")
    assert norm_in.shape == (32, 32, 3)
    assert np.isfinite(norm_in).all()

    # 4. ZScore
    norm_z = normalize_image(arr, method="zscore")
    assert np.isclose(np.mean(norm_z), 0.0, atol=1e-5)

    # 5. None
    arr_uint8 = np.array([[0, 255]], dtype=np.uint8)
    norm_none = normalize_image(arr_uint8, method="none")
    assert np.isclose(norm_none.max(), 1.0)


@pytest.mark.skipif(not CHECKPOINT_PATH.exists(), reason="Checkpoint file not found")
def test_direct_inference_arbitrary_dimensions():
    """Verify spatial preservation when image size is not divisible by 32."""
    model, _ = load_oil_spill_model(CHECKPOINT_PATH, device="cpu")

    # Non-divisible-by-32 dimensions (e.g. 177 x 243)
    odd_h, odd_w = 177, 243
    arr = np.random.uniform(0.0, 1.0, size=(odd_h, odd_w, 3)).astype(np.float32)

    prob_map = predict_patch_direct(arr, model, device=torch.device("cpu"))

    assert prob_map.shape == (odd_h, odd_w)
    assert np.all(prob_map >= 0.0) and np.all(prob_map <= 1.0)
    assert np.isfinite(prob_map).all()


@pytest.mark.skipif(not CHECKPOINT_PATH.exists(), reason="Checkpoint file not found")
def test_tiled_inference_large_image():
    """Verify tiled inference seamless stitching on large dimensions."""
    model, _ = load_oil_spill_model(CHECKPOINT_PATH, device="cpu")

    large_h, large_w = 550, 620
    arr = np.random.uniform(0.0, 1.0, size=(large_h, large_w, 3)).astype(np.float32)

    prob_map = predict_tiled(
        arr,
        model=model,
        device=torch.device("cpu"),
        tile_size=256,
        overlap=64,
        batch_size=2,
    )

    assert prob_map.shape == (large_h, large_w)
    assert np.all(prob_map >= 0.0) and np.all(prob_map <= 1.0)
    assert np.isfinite(prob_map).all()


@pytest.mark.skipif(not CHECKPOINT_PATH.exists(), reason="Checkpoint file not found")
def test_predict_oil_spill_end_to_end_png(sample_png_path: Path):
    """Verify end-to-end inference pipeline on a PNG file."""
    res = predict_oil_spill(
        image_input=sample_png_path,
        checkpoint_path=CHECKPOINT_PATH,
        device="cpu",
        threshold=0.5,
        norm_method="percentile",
        use_tiling=False,
    )

    assert isinstance(res, PredictionResult)
    assert res.original_image.shape == (256, 256)
    assert res.probability_map.shape == (256, 256)
    assert res.binary_mask.shape == (256, 256)
    assert set(np.unique(res.binary_mask)).issubset({0, 1})
    assert "inference_time_ms" in res.metadata
    assert res.metadata["threshold"] == 0.5


@pytest.mark.skipif(not CHECKPOINT_PATH.exists(), reason="Checkpoint file not found")
def test_predict_oil_spill_end_to_end_geotiff(sample_geotiff_path: Path):
    """Verify end-to-end inference on GeoTIFF with tiled execution."""
    res = predict_oil_spill(
        image_input=sample_geotiff_path,
        checkpoint_path=CHECKPOINT_PATH,
        device="cpu",
        threshold=0.5,
        tile_size=256,
        overlap=32,
        use_tiling=True,
    )

    assert res.probability_map.shape == (300, 300)
    assert res.binary_mask.shape == (300, 300)
    assert res.metadata["is_geotiff"] is True
    assert res.metadata["crs"] == "EPSG:4326"


def test_visualization_utilities(tmp_path: Path):
    """Verify overlay creation, 3-panel figure generation, and disk saving."""
    orig = np.random.randint(0, 255, size=(128, 128), dtype=np.uint8)
    prob = np.random.uniform(0, 1, size=(128, 128)).astype(np.float32)
    mask = (prob > 0.5).astype(np.uint8)

    # 1. Overlay
    overlay = create_overlay(orig, mask)
    assert overlay.shape == (128, 128, 3)
    assert overlay.dtype == np.uint8

    # 2. Figure
    fig = create_prediction_figure(orig, prob, mask, metadata={"threshold": 0.5})
    assert fig is not None

    # 3. Save
    save_path = tmp_path / "overlay.png"
    out_file = save_prediction_visualization(fig, save_path)
    assert out_file.exists()
    assert out_file.stat().st_size > 0
