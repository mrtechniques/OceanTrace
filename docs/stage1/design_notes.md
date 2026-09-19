# Stage 1 — Design & Technical Notes

## SAR Oil-Spill Detection

### Why Sentinel-1?

- **Free & open access** via ESA Copernicus Data Space
- **C-band (5.4 GHz)** penetrates clouds and operates day/night
- **GRD IW mode** — 10 m resolution, 250 km swath — optimal balance for spill mapping
- Spills appear as **low-backscatter dark patches** (σ⁰ < surrounding sea)

### Pipeline Decisions

| Step | Choice | Rationale |
|------|--------|-----------|
| Preprocessing | rasterio (Python) + optional SNAP | SNAP is gold-standard; rasterio allows SNAP-free fallback |
| Speckle filter | Refined-Lee 7×7 | Best trade-off between edge preservation and speckle suppression |
| Segmentation | YOLOv8/v11-seg | Fast, well-supported, works on image chips |
| Chipping | 640×640 px, 64 px overlap | Matches YOLO default input; overlap prevents edge artefacts |
| Normalisation | Percentile (2nd–98th) | Robust to outliers in SAR backscatter |
| Output CRS | EPSG:4326 | Universal; downstream drift model expects WGS84 |

### Known Lookalikes (False Positive Sources)

| Phenomenon | Appearance | Discrimination Strategy |
|------------|-----------|------------------------|
| Natural biogenic slicks (algae) | Thin, irregular | Wind speed context (< 2 m/s → natural slick more likely) |
| Wind shadows | Linear, directional | Orientation relative to wind vector |
| Rain cells | Circular, fuzzy | Correlation with weather radar / ERA5 precip |
| Low-wind areas | Large, amorphous | Requires metocean validation |

### Geometric Properties to Extract (per spill polygon)

- **Area** (m²) — CRS-aware geodesic
- **Perimeter** (m)
- **Centroid** (lon, lat)
- **Bounding box** (min/max lon/lat)
- **Elongation** (major axis / minor axis)
- **Circularity** (4π·Area / Perimeter²)
- **Scene timestamp** (UTC) — critical for drift hindcasting
- **Confidence score** — YOLO mask confidence
- **Backscatter statistics** — mean, std σ⁰ inside mask

### Data Flow Diagram

```
S1A_IW_GRDH_*.SAFE.zip
        │
        ▼  calibrate.py
  sigma0 GeoTIFF (10 m, linear)
        │
        ▼  speckle_filter.py
  Refined-Lee filtered GeoTIFF
        │
        ▼  chip_generator.py (utils)
  640×640 chips + positions
        │
        ▼  predict.py (YOLO)
  Per-chip masks + confidence
        │
        ▼  mask_refine.py
  Cleaned binary mask GeoTIFF
        │
        ▼  geo_properties.py
  GeoJSON FeatureCollection
  {geometry, area_m2, centroid, timestamp, ...}
        │
        └──▶ data/processed/masks/
             data/processed/features/
```

## Open Questions / To Be Resolved

1. **Dataset format** — YOLO requires `.yaml` dataset definition. Decide after dataset inspection whether labels exist in polygon, bounding-box, or pixel-mask format.
2. **Public labelled datasets** — Candidates: MADOS, SOS (Sentinel-1 Oil Spill), SAR-Ship. Inspect before committing to format.
3. **SNAP vs. pure-Python** — SNAP is more accurate for terrain correction; rasterio-only path is more portable. Final decision after evaluating SAR scene quality.
4. **GPU availability** — Training plan depends on whether a CUDA GPU is available.
