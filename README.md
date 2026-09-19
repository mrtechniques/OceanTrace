# OceanTrace 🛰️🌊

> **SIH 2026 · Problem Statement 26143**
>
> *Leveraging satellite imagery to determine oil spills at sea along with AIS data correlations to identify the vessel responsible for the spill.*

---

## Overview

OceanTrace is an end-to-end geospatial intelligence system that fuses **Sentinel-1 SAR satellite imagery** with **AIS vessel tracking data** to automatically detect marine oil spills and probabilistically identify the responsible vessel.

```
Sentinel-1 SAR / EO imagery
  └── Stage 1: Oil-Spill Detection & Segmentation          ← YOU ARE HERE
        └── Stage 2: Spill Characterisation & Drift Modelling
              └── Stage 3: AIS Trajectory Reconstruction
                    └── Stage 4: Candidate Vessel Correlation & Scoring
                          └── Stage 5: Interactive GIS Dashboard (FastAPI + React)
```

---

## System Architecture (Planned)

| Stage | Module | Key Technologies |
|-------|--------|-----------------|
| 1 | SAR Preprocessing & Oil-Spill Detection | Sentinel-1, PyTorch, YOLO Segmentation |
| 2 | Spill Drift & Hindcast Modelling | OpenDrift, ERA5 winds/currents, CMEMS ocean data |
| 3 | AIS Data Ingestion & Trajectory Reconstruction | pyais, PostGIS, GeoPandas |
| 4 | Vessel Correlation & Evidence Scoring | Spatial-temporal analysis, behavioural heuristics |
| 5 | Interactive GIS Dashboard | FastAPI, PostgreSQL/PostGIS, React + TypeScript, Leaflet / DeckGL |

---

## Stage 1 — Satellite Oil-Spill Detection

### Goal

```
Sentinel-1 SAR image
  → Preprocessing (calibration, speckle filter, terrain correction)
  → Oil-Spill Segmentation  (YOLO-based instance segmentation)
  → Spill Mask (binary + confidence map)
  → Geometric Properties (area, perimeter, centroid, bounding box — CRS-aware)
```

### Scientific Background

Sentinel-1 C-band SAR imagery detects oil spills via the **Bragg scattering** mechanism:
- Crude/refined oil dampens short ocean surface waves, reducing radar backscatter.
- Oil-covered water appears as **dark patches** against the surrounding brighter sea surface.
- Lookalikes (natural slicks, wind shadows, rain cells, biogenic films) must be discriminated.

### Pipeline Design

```
data/raw/sar/            ← Input: Sentinel-1 GRD or SLC scenes (.zip / .SAFE)
        │
        ▼
src/detection/preprocessing/
  ├── calibrate.py       ← Radiometric calibration → σ⁰ (sigma-nought)
  ├── speckle_filter.py  ← Lee / Refined-Lee / Frost filter
  └── terrain_correct.py ← Range-Doppler terrain correction (DEM)
        │
        ▼
src/detection/segmentation/
  ├── model.py           ← YOLO segmentation wrapper (Ultralytics API)
  ├── predict.py         ← Inference on preprocessed GeoTIFF chips
  └── dataset.py         ← Dataset loader (format TBD after inspection)
        │
        ▼
src/detection/postprocessing/
  ├── mask_refine.py     ← Morphological clean-up, polygon smoothing
  └── geo_properties.py  ← CRS-aware area, perimeter, centroid extraction
        │
        ▼
data/processed/masks/    ← Output: GeoJSON / GeoTIFF spill masks
```

### Module Layout

```
OceanTrace/
├── src/
│   ├── detection/             # Stage 1
│   │   ├── preprocessing/
│   │   ├── segmentation/
│   │   ├── postprocessing/
│   │   └── utils/
│   ├── drift/                 # Stage 2 (planned)
│   ├── ais/                   # Stage 3 (planned)
│   ├── api/                   # Stage 4 (planned) — FastAPI
│   └── gis/                   # Stage 5 (planned) — PostGIS helpers
├── data/
│   ├── raw/                   # Never committed (see .gitignore)
│   │   ├── sar/
│   │   └── eo/
│   ├── processed/
│   │   ├── masks/
│   │   └── features/
│   └── interim/
├── models/
│   ├── checkpoints/           # Trained weights (use DVC / S3)
│   └── configs/               # YOLO .yaml model configs
├── notebooks/
│   ├── stage1_detection/      # EDA, chip inspection, baseline runs
│   ├── stage2_drift/
│   └── stage3_ais/
├── scripts/                   # CLI entry points
├── tests/
│   ├── test_detection/
│   ├── test_ais/
│   └── test_drift/
├── configs/                   # Global YAML configs (model, pipeline)
├── docs/
│   ├── stage1/
│   ├── stage2/
│   └── stage3/
├── .gitignore
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Getting Started

### Prerequisites

- Python ≥ 3.10 (tested on 3.13)
- [ESA SNAP](https://step.esa.int/main/download/snap-download/) — for full SAR preprocessing chain (optional for pure-Python path)
- GPU recommended for model training (CUDA ≥ 11.8)

### Environment Setup

```bash
# Clone the repository
git clone https://github.com/your-org/oceantrace.git
cd oceantrace

# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Install Stage 1 dependencies
pip install -r requirements.txt
```

### Data

Raw Sentinel-1 scenes should be placed in `data/raw/sar/`.
They are excluded from version control via `.gitignore`.

Download sources:
- [Copernicus Data Space Ecosystem](https://dataspace.copernicus.eu/)
- [Alaska Satellite Facility (ASF) Vertex](https://search.asf.alaska.edu/)
- [ESA Sentinel-1 SciHub](https://scihub.copernicus.eu/)

Recommended product type: **Sentinel-1 GRD IW** (Ground Range Detected, Interferometric Wide swath)

---

## Development Roadmap

- [x] Stage 1 — Repository scaffold & environment setup
- [ ] Stage 1 — Dataset inspection notebook
- [ ] Stage 1 — SAR preprocessing pipeline
- [ ] Stage 1 — YOLO segmentation baseline
- [ ] Stage 1 — Geometric property extraction
- [ ] Stage 2 — Drift modelling integration
- [ ] Stage 3 — AIS data ingestion & reconstruction
- [ ] Stage 4 — Vessel correlation & scoring
- [ ] Stage 5 — Interactive GIS dashboard

---

## Contributing

This project follows a modular architecture. Each stage is independently developable and testable. See `docs/` for stage-specific design documents.

---

## License

MIT License — see `LICENSE` for details.

---

## Acknowledgements

- ESA Copernicus Programme — Sentinel-1 SAR data
- Ultralytics — YOLOv8/v11 segmentation framework
- OpenDrift — Lagrangian drift modelling
- CMEMS — Copernicus Marine Environment Monitoring Service
