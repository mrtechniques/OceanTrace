# OceanTrace — Maritime Intelligence Web Application

> **SIH 2026 · Problem Statement 26143**  
> *Leveraging Sentinel-1 SAR satellite imagery to determine oil spills at sea along with AIS data correlations to identify the responsible vessel.*

---

## 🎨 Design System & Color Tokens (Strict 60:30:10 Ratio)

This interface is built on a **clean, editorial maritime intelligence** design philosophy — eschewing dark-mode neon sci-fi tropes in favor of refined cartographic elegance, high-contrast readability, and purpose-driven telemetry:

| Weight | Token Name | Hex Code | Visual Application |
| :--- | :--- | :--- | :--- |
| **60% Dominant** | **Warm Ivory** | `#EAE6DE` / `#F7F5F0` | Main application canvas, panel backgrounds, ocean basemap tones, subtle paper cards, and generous negative whitespace. |
| **30% Secondary** | **Deep Editorial Blue** | `#226192` / `#0F293F` | Site header chrome, primary typography, table headers, hairline structural borders (`1px`), and navigation frames. |
| **10% Accent** | **Coral Orange** | `#EF8557` | Primary action buttons ("Analyze Scene", "Export Dossier"), detected SAR oil-spill polygons, culprit attribution badge, and urgent alert indicators. |

### Button Precision & Centering
All buttons use `display: inline-flex; align-items: center; justify-content: center; gap: 0.5rem; text-align: center;` with strict line-height centering and cubic-bezier micro-interaction states.

---

## 🧭 Workflow Architecture (Only 3 Required Pages)

1. **Surveillance & Detection Monitor (`/monitor`)**
   - High-contrast maritime GIS map displaying Sentinel-1 SAR acquisition swath and detected oil-spill polygons.
   - Scene ingestion card with radiometric calibration ($\sigma^0$) and speckle filter (Refined-Lee 7×7) controls.
   - Detected incidents feed with geodesic surface area ($\text{km}^2$), perimeter, and U-Net ResNet34 confidence rating.

2. **Drift & Hindcast Forensics (`/forensics`)**
   - Backward Lagrangian hydrodynamic drift modeling (OpenDrift + CMEMS ocean currents + ERA5 surface winds).
   - Interactive time-scrubber slider (scrubbing from detection $T_0$ backward to $T_{-14h}$ estimated release locus).
   - Slick morphometry panel (perimeter, circularity, elongation, radar backscatter decibel contrast).

3. **Vessel Attribution Dossier (`/attribution`)**
   - Correlation table ranking candidate ships by Closest Point of Approach (CPA) and trajectory intersection.
   - Prominent highlight of **Primary Culprit (M/T Ocean Crown · 94.2% Probability)** detailing anomalous speed deceleration ($14.2 \to 5.1\text{ kn}$) and deliberate 118-minute AIS transponder blackout.
   - Interactive **Legal Evidence Dossier** export preview with SHA-256 cryptographic provenance hash and court-admissible MARPOL Annex I chain of custody summary.

---

## 🚀 Running the Web Application

To open and run the application:
- Simply double-click **`ui/index.html`** to launch it in any web browser (Google Chrome, Microsoft Edge, Firefox, Safari).
- Or run any local static file server from the repository root:
  ```bash
  # Using Python (standard library)
  python -m http.server 3000 --directory ui

  # Or using VS Code Live Server / npx serve
  npx serve ui
  ```
