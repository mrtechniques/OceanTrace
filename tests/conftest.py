"""
pytest conftest.py — shared fixtures for the OceanTrace test suite.

Fixtures defined here are available to all test modules without importing.
Add session-scoped fixtures (e.g., temp directories, small synthetic SAR arrays)
here as the test suite grows.
"""
import pytest
import numpy as np


@pytest.fixture(scope="session")
def synthetic_sar_chip():
    """
    Returns a small synthetic SAR backscatter chip (float32, single-band)
    shaped (1, 256, 256) in the format [C, H, W].

    The chip simulates a dark-patch oil spill surrounded by brighter sea clutter.
    Values are in linear power scale (σ⁰), roughly 0.0 – 0.3.
    """
    rng = np.random.default_rng(seed=42)
    chip = rng.uniform(0.05, 0.30, size=(1, 256, 256)).astype(np.float32)
    # Inject a synthetic "dark patch" spill region
    chip[0, 80:160, 80:170] = rng.uniform(0.001, 0.02, size=(80, 90)).astype(np.float32)
    return chip
