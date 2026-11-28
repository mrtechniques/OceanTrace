# OceanTrace 🛰️🌊

> **SIH 2026 · Problem Statement 26143**
>
> *Leveraging Sentinel-1 SAR satellite imagery to detect marine oil spills and correlating AIS vessel trajectories to identify candidate vessels.*

---

## Overview

OceanTrace is an end-to-end geospatial intelligence platform that combines **Sentinel-1 SAR oil spill segmentation** (PyTorch U-Net with a ResNet34 encoder) with **AIS vessel tracking** and **spatio-temporal correlation** inside a unified FastAPI backend and interactive Leaflet GIS web interface.

```text
Sentinel-1 SAR / Optical Imagery (PNG, JPG, GeoTIFF)
  └── Preprocessing & Tiled/Direct Inference (ResNet34 U-Net)
        └── Binary Spill Mask + Probability Map + 3-Panel Overlay
              └── Spatio-Temporal AIS Correlation (CPA, Timing, Dark Gaps)
                    └── Interactive Maritime GIS Dashboard (FastAPI + Leaflet UI)
```

---

## Key Capabilities & Architecture

| Component | Module | Status | Key Technologies |
|---|---|---|---|
| **SAR Oil-Spill Segmentation** | `src/detection/` | Implemented | PyTorch, `ResNet34UNet`, `rasterio`, OpenCV/PIL, Matplotlib |
| **Inference CLI** | `scripts/predict_spill.py` | Implemented | Python CLI for PNG/JPG/GeoTIFF prediction & overlays |
| **FastAPI Backend** | `src/api/` | Implemented | FastAPI, Uvicorn, Pydantic, Multipart Uploads, CORS |
| **AIS & Satellite Simulator** | `src/simulation/` | Implemented | Simulated AIS tracks, Sentinel-1 scene catalog, Haversine CPA correlation |
| **Interactive Web UI** | `ui/` | Implemented | HTML5/CSS3/ES6, Leaflet GIS, CartoDB Voyager basemap |
| **Drift Forensics (UI)** | `ui/js/components/forensics.js` | Prototype / UI | Interactive backward Lagrangian hindcast scrubber |

---

## Trained Model & Benchmark Metrics

- **Architecture:** `ResNet34UNet` (`resnet34` encoder, 3 input channels, 1 output logit channel)
- **Checkpoint:** `models/best_oil_spill_unet.pth` (Epoch 14, Best Validation Dice: `0.8255`)
- **Inference Modes:** Direct (256×256 / padded to multiples of 32) and overlap-blended tiled inference (`512×512` tiles, `64px` overlap) for large GeoTIFF scenes.
- **Established Test Set Evaluation Metrics:**

| Metric | Score |
|---|---|
| **Precision** | 87.76% |
| **Recall** | 89.40% |
| **F1-Score** | 88.57% |
| **Global Dice** | 88.57% |
| **Mean Dice** | 82.70% |
| **Global IoU** | 79.49% |
| **Mean IoU** | 73.27% |

> *Note: These are established model evaluation metrics on the validation/test benchmark, separate from per-image prediction confidence scores. Operational deployment requires validation against real-world SAR ground truth.*

---

## Repository Structure

```text
OceanTrace/
├── configs/
│   └── stage1_config.yaml         # Pipeline & preprocessing configuration
├── data/
│   ├── raw/sar/                   # Raw / sample Sentinel-1 SAR scenes
│   ├── interim/uploads/           # API uploaded imagery
│   └── processed/
│       ├── api_results/           # Persisted API predictions & visualizations
│       └── masks/                 # CLI prediction masks & overlays
├── docs/
│   └── stage1/design_notes.md     # Architecture & SAR design documentation
├── models/
│   └── best_oil_spill_unet.pth    # Trained ResNet34 U-Net weights (Git LFS)
├── scripts/
│   └── predict_spill.py           # Standalone CLI for oil spill inference
├── src/
│   ├── api/
│   │   ├── main.py                # FastAPI app factory, CORS, static UI mount
│   │   ├── config.py              # Environment-configurable paths & defaults
│   │   ├── dependencies.py        # Singleton ModelService lifecycle manager
│   │   ├── schemas.py             # Pydantic request/response schemas
│   │   └── routers/
│   │       ├── health.py          # GET /api/health, GET /api/model-info
│   │       ├── predict.py         # POST /api/predict, GET /api/results/{id}
│   │       ├── ais.py             # GET /api/ais/vessels, /api/ais/vessels/{mmsi}
│   │       ├── satellite.py       # GET /api/satellite/scenes (+ preview/download)
│   │       └── correlation.py     # POST /api/correlation/correlate
│   ├── detection/
│   │   ├── preprocessing/         # Image loading (PNG/JPG/GeoTIFF) & normalization
│   │   ├── segmentation/          # ResNet34UNet model & tiled/direct inference
│   │   └── utils/                 # 3-panel visualization & overlay utilities
│   └── simulation/
│       ├── models.py              # AIS, Sentinel-1, and correlation schemas
│       ├── providers.py           # AISSimulatorProvider & Sentinel1SimulatorProvider
│       └── correlation.py         # Spatial-temporal CPA & anomaly ranking engine
├── tests/
│   ├── conftest.py
│   ├── test_api/
│   │   ├── test_endpoints.py      # Inference, health, and metadata API tests
│   │   └── test_simulator.py      # AIS, satellite, and correlation API tests
│   └── test_detection/
│       ├── test_unet.py           # Architecture & strict checkpoint loading tests
│       ├── test_pipeline.py       # Preprocessing, tiling, & end-to-end tests
│       └── test_segmentation.py   # Chip-level segmentation tests
├── ui/
│   ├── index.html                 # Maritime Intelligence UI entry point
│   ├── css/main.css               # 60:30:10 Warm Ivory / Deep Blue / Coral theme
│   └── js/
│       ├── api.js                 # Centralized FastAPI client
│       ├── app.js                 # Router, live UTC clock, backend health check
│       ├── data.js                # Reference SAR scenes, incidents, drift data
│       └── components/
│           ├── monitor.js         # Upload, U-Net inference, AIS map & results
│           ├── forensics.js       # Drift hindcast scrubber & morphometry
│           ├── attribution.js     # Candidate vessel ranking & map
│           └── dossierModal.js    # Legal evidence dossier preview
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Getting Started

### Prerequisites

- Python ≥ 3.10 (tested on Python 3.13)
- Virtual environment (`.venv`) with dependencies installed

### Environment Setup

```powershell
# Clone the repository
git clone https://github.com/your-org/oceantrace.git
cd oceantrace

# Create and activate virtual environment (Windows PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

---

## Running the Application

### 1. Start the FastAPI Backend & Integrated Web UI

```powershell
.venv\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
```

Once running, open in your browser:
- **Integrated Web UI:** `http://127.0.0.1:8000/ui/index.html` (or `http://127.0.0.1:8000/`)
- **Interactive API Docs (Swagger):** `http://127.0.0.1:8000/docs`

### 2. Run Standalone CLI Inference

```powershell
.venv\Scripts\python.exe scripts/predict_spill.py `
  --input data/raw/sar/synthetic_sar_sample.png `
  --threshold 0.5 `
  --norm percentile `
  --output-dir data/processed/masks
```

---

## REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Backend health, model load status, epoch, and compute device (`cpu`/`cuda`) |
| `GET` | `/api/model-info` | Model architecture, encoder, input resolution, and benchmark metrics |
| `POST` | `/api/predict` | Upload PNG/JPG/GeoTIFF (`multipart/form-data`) for U-Net segmentation |
| `GET` | `/api/results/{prediction_id}` | Retrieve prediction metadata (`original`, `mask`, `overlay` asset URLs) |
| `GET` | `/api/ais/vessels` | Retrieve AIS vessel positions & tracks (supports `min_lat`, `min_lon`, `max_lat`, `max_lon`) |
| `GET` | `/api/ais/vessels/{mmsi}` | Retrieve vessel details and trajectory by 9-digit MMSI |
| `GET` | `/api/satellite/scenes` | Search Sentinel-1 scenes by bounding box and date range |
| `GET` | `/api/satellite/scenes/{scene_id}/preview` | Retrieve 256×256 SAR scene preview thumbnail |
| `GET` | `/api/satellite/scenes/{scene_id}/download` | Download scene raster compatible with `POST /api/predict` |
| `POST` | `/api/correlation/correlate` | Rank nearby candidate vessels using CPA, time delta, and AIS gap evidence |

---

## Running Automated Tests

Run the full test suite (37 tests covering U-Net architecture, preprocessing, tiled/direct inference, FastAPI endpoints, AIS/satellite simulator, and correlation):

```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
```

---

## Configuration & External Data Credentials

The backend uses environment variables in `src/api/config.py` (with sensible defaults):
- `OCEANTRACE_MODEL_PATH` (default: `models/best_oil_spill_unet.pth`)
- `OCEANTRACE_DEVICE` (default: auto-detect CUDA/CPU)
- `OCEANTRACE_THRESHOLD` (default: `0.5`)
- `OCEANTRACE_NORM_METHOD` (default: `percentile`)
- `OCEANTRACE_TILE_SIZE` (default: `512`)
- `OCEANTRACE_OVERLAP` (default: `64`)

By default, AIS and Sentinel-1 services run using the built-in local simulator (`src/simulation/providers.py`). For live production data feeds, external provider credentials would be required:
- **Copernicus Data Space Ecosystem (CDSE):** `COPERNICUS_CDSE_CLIENT_ID`, `COPERNICUS_CDSE_CLIENT_SECRET`
- **Live AIS Feed (e.g., AISStream / Spire):** `AISSTREAM_API_KEY` or `SPIRE_AIS_API_KEY`

---

## Development Roadmap

- [x] Stage 1 — Repository scaffold & environment setup
- [x] Stage 1 — ResNet34 U-Net architecture & strict checkpoint integration
- [x] Stage 1 — SAR preprocessing, tiled GeoTIFF inference, & CLI (`scripts/predict_spill.py`)
- [x] Backend — FastAPI service (`/api/health`, `/api/model-info`, `/api/predict`, `/api/results/{id}`)
- [x] Frontend — Maritime Intelligence UI integration (`ui/`) with live upload & visualizer
- [x] Simulator — AIS vessel tracking, Sentinel-1 catalog, & spatio-temporal correlation APIs
- [ ] Live Feeds — Connect live Copernicus CDSE & real-time AIS WebSocket providers
- [ ] Stage 2 — Backend OpenDrift hydrodynamic hindcasting with CMEMS/ERA5 data

---

## Acknowledgements

- ESA Copernicus Programme — Sentinel-1 SAR data
- OpenDrift — Lagrangian drift modelling
- CMEMS — Copernicus Marine Environment Monitoring Service
