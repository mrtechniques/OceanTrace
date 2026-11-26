/**
 * Surveillance & Detection Monitor Component (Page 1)
 */
const MonitorComponent = {
  map: null,
  spillLayer: null,
  sarLayer: null,

  render() {
    const scene = OceanTraceData.sarScenes[0];
    const incidents = Object.values(OceanTraceData.incidents);

    return `
      <div class="split-view">
        <!-- Main GIS Map Viewport -->
        <div class="split-map-pane">
          <!-- Floating Map Toolbar -->
          <div class="map-toolbar">
            <span style="font-family: var(--font-mono); font-size: 0.72rem; font-weight: 700; color: var(--blue-900); padding: 0 0.4rem; text-transform: uppercase;">Layers:</span>
            <button class="map-tool-btn active" id="btn-toggle-sar">SAR Backscatter (σ⁰)</button>
            <button class="map-tool-btn active" id="btn-toggle-slick">Spill Mask (U-Net)</button>
            <button class="map-tool-btn" id="btn-toggle-wind">Wind / Current Vectors</button>
            <div style="width: 1px; height: 18px; background: var(--border-medium); margin: 0 0.2rem;"></div>
            <button class="map-tool-btn" id="btn-reset-map" title="Reset View">
              <i data-lucide="crosshair" style="width: 14px; height: 14px; margin-right: 4px;"></i> Reset Bounds
            </button>
          </div>

          <!-- The Leaflet Map Canvas -->
          <div id="monitor-map" class="map-canvas"></div>

          <!-- Bottom HUD Stats Pill -->
          <div class="map-hud-pill">
            <div><span style="color: var(--blue-300);">SCENE:</span> ${scene.id}</div>
            <div><span style="color: var(--blue-300);">ORBIT:</span> ${scene.orbit}</div>
            <div><span style="color: var(--blue-300);">RES:</span> ${scene.resolution}</div>
            <div><span style="color: var(--blue-300);">POL:</span> ${scene.polarization}</div>
          </div>
        </div>

        <!-- Right Side Panel: Ingestion & Incidents -->
        <div class="split-side-pane">
          <!-- Ingestion & Preprocessing Card -->
          <div class="card">
            <div class="card-header">
              <div>
                <h3 class="card-title">SAR Scene Ingestion</h3>
                <p class="card-subtitle">Sentinel-1 C-Band Preprocessing Chain</p>
              </div>
              <span class="status-pill live">
                <span class="pulse-dot"></span> Ready
              </span>
            </div>

            <div class="form-group">
              <label class="form-label">Satellite Target Scene</label>
              <select id="select-sar-scene" class="form-select">
                ${OceanTraceData.sarScenes.map(s => `
                  <option value="${s.id}">${s.name} (${s.id.substring(0, 24)}...)</option>
                `).join('')}
              </select>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; margin-bottom: 0.85rem;">
              <div class="form-group" style="margin-bottom: 0;">
                <label class="form-label">Calibration</label>
                <select class="form-select" disabled>
                  <option>Sigma Nought (σ⁰)</option>
                </select>
              </div>
              <div class="form-group" style="margin-bottom: 0;">
                <label class="form-label">Speckle Filter</label>
                <select class="form-select" disabled>
                  <option>Refined-Lee 7×7</option>
                </select>
              </div>
            </div>

            <button id="btn-run-inference" class="btn btn-primary btn-full" style="margin-top: 0.5rem;">
              <i data-lucide="satellite" style="width: 16px; height: 16px;"></i>
              Analyze Scene (U-Net ResNet34)
            </button>
            <div id="inference-progress" style="display: none; margin-top: 0.6rem; font-size: 0.76rem; color: var(--blue-700); text-align: center;">
              <div style="height: 4px; background: var(--ivory-300); border-radius: 2px; overflow: hidden; margin-bottom: 4px;">
                <div style="height: 100%; width: 100%; background: var(--coral-500); animation: pulse-ring 1s infinite;"></div>
              </div>
              Running 256×256 chipping & ResNet34-UNet semantic segmentation...
            </div>
          </div>

          <!-- Detected Incidents List -->
          <div>
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem;">
              <h4 style="font-family: var(--font-serif); font-size: 1.05rem; font-weight: 600; color: var(--blue-900);">
                Detected Slick Incidents (${incidents.length})
              </h4>
              <span style="font-size: 0.72rem; color: var(--blue-700); font-family: var(--font-mono);">CRS: EPSG:4326</span>
            </div>

            <div style="display: flex; flex-direction: column; gap: 0.75rem;">
              ${incidents.map(inc => `
                <div class="incident-card ${inc.id === OceanTraceData.activeIncidentId ? 'selected' : ''}" data-incident-id="${inc.id}">
                  <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                      <span style="font-family: var(--font-mono); font-weight: 700; color: var(--blue-900); font-size: 0.88rem;">${inc.id}</span>
                      <span class="status-pill coral">${inc.severity}</span>
                    </div>
                    <span style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--coral-600); font-weight: 700;">
                      ${inc.modelConfidence}% conf
                    </span>
                  </div>

                  <p style="font-size: 0.78rem; color: var(--blue-700); margin-top: 0.35rem;">
                    <i data-lucide="map-pin" style="width: 12px; height: 12px; display: inline; vertical-align: -1px; margin-right: 2px;"></i>
                    ${inc.locationName}
                  </p>

                  <div class="incident-meta-grid">
                    <div class="meta-field">
                      <span class="meta-label">Geodesic Area</span>
                      <span class="meta-value" style="color: var(--coral-600);">${inc.areaKm2} km²</span>
                    </div>
                    <div class="meta-field">
                      <span class="meta-label">Perimeter</span>
                      <span class="meta-value">${inc.perimeterKm} km</span>
                    </div>
                    <div class="meta-field">
                      <span class="meta-label">SAR Contrast</span>
                      <span class="meta-value">-${inc.contrastDb} dB</span>
                    </div>
                    <div class="meta-field">
                      <span class="meta-label">Status</span>
                      <span class="meta-value" style="font-size: 0.72rem; color: var(--blue-600);">${inc.status}</span>
                    </div>
                  </div>

                  <div style="display: flex; gap: 0.5rem; margin-top: 0.25rem;">
                    <button class="btn btn-secondary btn-sm btn-full btn-inspect-drift" data-incident-id="${inc.id}">
                      Inspect & Model Drift
                      <i data-lucide="arrow-right" style="width: 14px; height: 14px;"></i>
                    </button>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        </div>
      </div>
    `;
  },

  initMap() {
    const scene = OceanTraceData.sarScenes[0];
    const incident = OceanTraceData.incidents[OceanTraceData.activeIncidentId];

    if (this.map) {
      this.map.remove();
    }

    this.map = L.map('monitor-map', {
      zoomControl: true,
      attributionControl: false
    }).setView(incident.centroid, 10);

    // Cartographic Maritime Tile Layer (Warm Ivory Tone)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      maxZoom: 18,
      subdomains: 'abcd'
    }).addTo(this.map);

    // Draw Sentinel-1 SAR Bounding Box
    this.sarLayer = L.rectangle(scene.bounds, {
      color: '#226192',
      weight: 1.5,
      dashArray: '6, 6',
      fillColor: '#226192',
      fillOpacity: 0.05
    }).addTo(this.map);
    this.sarLayer.bindTooltip(`Sentinel-1A Swath Footprint [${scene.orbit}]`, { permanent: false, direction: 'top' });

    // Draw Oil Spill Polygon (Synthetic realistic multi-polygon in Coral Orange)
    const spillPolygonCoords = [
      [24.845, 57.210],
      [24.830, 57.265],
      [24.805, 57.285],
      [24.780, 57.250],
      [24.795, 57.215],
      [24.820, 57.195]
    ];

    this.spillLayer = L.polygon(spillPolygonCoords, {
      color: '#EF8557',
      weight: 2.5,
      fillColor: '#EF8557',
      fillOpacity: 0.45,
      dashArray: '4, 2'
    }).addTo(this.map);

    this.spillLayer.bindPopup(`
      <div style="font-family: var(--font-sans); padding: 4px;">
        <div style="font-weight: 700; color: #226192; font-size: 13px; margin-bottom: 4px;">
          Incident ${incident.id} (U-Net ResNet34)
        </div>
        <div style="font-family: var(--font-mono); font-size: 11px; line-height: 1.5;">
          • Area: <strong>${incident.areaKm2} km²</strong><br>
          • Perimeter: <strong>${incident.perimeterKm} km</strong><br>
          • Confidence: <strong>${incident.modelConfidence}%</strong><br>
          • Backscatter σ⁰: <strong>${incident.minBackscatterDb} dB</strong>
        </div>
      </div>
    `);

    // Add pulse marker at centroid
    const pulseIcon = L.divIcon({
      className: 'custom-pulse-marker',
      html: `
        <div style="width: 20px; height: 20px; border-radius: 50%; background: rgba(239, 133, 87, 0.5); display: flex; align-items: center; justify-content: center;">
          <div style="width: 8px; height: 8px; border-radius: 50%; background: #EF8557;"></div>
        </div>
      `,
      iconSize: [20, 20],
      iconAnchor: [10, 10]
    });
    L.marker(incident.centroid, { icon: pulseIcon }).addTo(this.map);
  },

  bindEvents() {
    // Inspect and Model Drift buttons
    document.querySelectorAll('.btn-inspect-drift').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const incId = e.currentTarget.dataset.incidentId;
        OceanTraceData.activeIncidentId = incId;
        App.navigateTo('forensics');
      });
    });

    // Run inference button
    const runBtn = document.getElementById('btn-run-inference');
    if (runBtn) {
      runBtn.addEventListener('click', () => {
        const prog = document.getElementById('inference-progress');
        runBtn.disabled = true;
        prog.style.display = 'block';
        setTimeout(() => {
          prog.style.display = 'none';
          runBtn.disabled = false;
          alert('SAR Chipping & Inference Complete. 2 discrete spill clusters segmented. Minimum detected area: 3.41 km².');
        }, 1200);
      });
    }

    // Reset view
    const resetBtn = document.getElementById('btn-reset-map');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        const incident = OceanTraceData.incidents[OceanTraceData.activeIncidentId];
        this.map.setView(incident.centroid, 10);
      });
    }
  }
};
