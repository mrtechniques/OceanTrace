/**
 * OceanTrace Centralized API Client
 * Facilitates communication with the FastAPI backend for health checks,
 * model telemetry, image prediction, and asset retrieval.
 */

const OceanTraceApi = {
  /**
   * Determine the API base URL dynamically.
   * Allows override via window.OCEANTRACE_API_BASE or environment injection.
   */
  getBaseUrl() {
    if (window.OCEANTRACE_API_BASE) {
      return window.OCEANTRACE_API_BASE.replace(/\/+$/, '');
    }
    // If the frontend is served directly by the FastAPI backend (e.g., at :8000/ui)
    if (window.location.port === "8000" || window.location.pathname.startsWith("/ui")) {
      return window.location.origin;
    }
    // Default fallback to local FastAPI development server
    return "http://localhost:8000";
  },

  /**
   * GET /api/health
   * Check backend operational status and neural network readiness.
   */
  async checkHealth() {
    try {
      const res = await fetch(`${this.getBaseUrl()}/api/health`, {
        method: "GET",
        headers: { "Accept": "application/json" }
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      return await res.json();
    } catch (err) {
      console.warn("[OceanTrace API] Health check failed:", err.message);
      return {
        status: "offline",
        model_loaded: false,
        device: "unknown",
        error: err.message
      };
    }
  },

  /**
   * GET /api/model-info
   * Retrieve model architecture, encoder, and established benchmark metrics.
   */
  async getModelInfo() {
    try {
      const res = await fetch(`${this.getBaseUrl()}/api/model-info`, {
        method: "GET",
        headers: { "Accept": "application/json" }
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      return await res.json();
    } catch (err) {
      console.warn("[OceanTrace API] Model info fetch failed:", err.message);
      return null;
    }
  },

  /**
   * POST /api/predict
   * Upload a Sentinel-1 SAR scene or image (PNG, JPG, GeoTIFF) for U-Net segmentation.
   *
   * @param {File|Blob} file - The image file to analyze.
   * @param {Object} options - Inference parameters (threshold, normMethod, tileSize, overlap).
   * @returns {Promise<Object>} The prediction response payload.
   */
  async predictSpill(file, { threshold = 0.5, normMethod = "percentile", tileSize = 512, overlap = 64 } = {}) {
    if (!file) {
      throw new Error("No image file provided for inference.");
    }

    const formData = new FormData();
    formData.append("file", file, file.name || "uploaded_sar.png");
    formData.append("threshold", threshold.toString());
    formData.append("norm_method", normMethod);
    formData.append("tile_size", tileSize.toString());
    formData.append("overlap", overlap.toString());

    let res;
    try {
      res = await fetch(`${this.getBaseUrl()}/api/predict`, {
        method: "POST",
        body: formData,
      });
    } catch (networkErr) {
      throw new Error(
        `Backend server unreachable at ${this.getBaseUrl()}. Please ensure the FastAPI server is running.`
      );
    }

    if (!res.ok) {
      let detail = `Server responded with HTTP ${res.status} (${res.statusText})`;
      try {
        const errJson = await res.json();
        if (errJson.detail) {
          detail = errJson.detail;
        }
      } catch (_) {}
      throw new Error(detail);
    }

    const data = await res.json();
    return data;
  },

  /**
   * GET /api/results/{prediction_id}
   * Retrieve persisted prediction metadata by ID.
   */
  async getPredictionResult(predictionId) {
    const res = await fetch(`${this.getBaseUrl()}/api/results/${predictionId}`);
    if (!res.ok) {
      throw new Error(`Failed to retrieve prediction ${predictionId}: HTTP ${res.status}`);
    }
    return await res.json();
  },

  /**
   * Resolve an asset URL (e.g., /api/results/{id}/mask) to an absolute URL if needed.
   */
  resolveAssetUrl(url) {
    if (!url) return "";
    if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("data:") || url.startsWith("blob:")) {
      return url;
    }
    const cleanUrl = url.startsWith("/") ? url : `/${url}`;
    return `${this.getBaseUrl()}${cleanUrl}`;
  },

  /**
   * GET /api/ais/vessels
   * Retrieve live or simulated AIS vessel positions.
   */
  async getAISVessels(bbox = null) {
    try {
      let url = `${this.getBaseUrl()}/api/ais/vessels`;
      if (bbox) {
        const { minLat, minLon, maxLat, maxLon } = bbox;
        url += `?min_lat=${minLat}&min_lon=${minLon}&max_lat=${maxLat}&max_lon=${maxLon}`;
      }
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      return await res.json();
    } catch (err) {
      console.warn("[OceanTrace API] Failed to fetch AIS vessels:", err.message);
      return [];
    }
  },

  /**
   * GET /api/ais/vessels/{mmsi}
   */
  async getVesselDetails(mmsi) {
    const res = await fetch(`${this.getBaseUrl()}/api/ais/vessels/${mmsi}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}: Vessel ${mmsi} not found`);
    return await res.json();
  },

  /**
   * GET /api/satellite/scenes
   * Search Sentinel-1 satellite scenes.
   */
  async searchSatelliteScenes(filters = {}) {
    try {
      const params = new URLSearchParams();
      if (filters.minLat != null) params.append("min_lat", filters.minLat);
      if (filters.minLon != null) params.append("min_lon", filters.minLon);
      if (filters.maxLat != null) params.append("max_lat", filters.maxLat);
      if (filters.maxLon != null) params.append("max_lon", filters.maxLon);
      if (filters.startDate) params.append("start_date", filters.startDate);
      if (filters.endDate) params.append("end_date", filters.endDate);

      const qs = params.toString();
      const url = `${this.getBaseUrl()}/api/satellite/scenes${qs ? `?${qs}` : ''}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn("[OceanTrace API] Satellite scene search failed:", err.message);
      return [];
    }
  },

  /**
   * POST /api/correlation/correlate
   * Compare detected spill coordinates and observation timestamp against AIS tracks.
   */
  async correlateVesselsWithSpill(spillLat, spillLon, spillTimeUtc, radiusKm = 50.0) {
    try {
      const res = await fetch(`${this.getBaseUrl()}/api/correlation/correlate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          spill_latitude: spillLat,
          spill_longitude: spillLon,
          spill_timestamp_utc: spillTimeUtc,
          search_radius_km: radiusKm,
          max_time_diff_hours: 24.0
        })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn("[OceanTrace API] Correlation request failed:", err.message);
      return [];
    }
  }
};

window.OceanTraceApi = OceanTraceApi;
