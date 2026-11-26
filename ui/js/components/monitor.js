/**
 * Surveillance & Detection Monitor Component (Page 1)
 */
const MonitorComponent = {
  map: null,
  spillLayer: null,
  sarLayer: null,
  aisLayerGroup: null,

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
            <button class="map-tool-btn active" id="btn-toggle-ais">Live AIS Vessels</button>
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
                <h3 class="card-title">SAR Scene Ingestion & Inference</h3>
                <p class="card-subtitle">Sentinel-1 C-Band PyTorch U-Net (ResNet34)</p>
              </div>
              <span class="status-pill live" id="ingestion-status-badge">
                <span class="pulse-dot"></span> Ready
              </span>
            </div>

            <!-- Ingestion Mode Selector (Upload vs Catalog) -->
            <div style="display: flex; gap: 0.5rem; margin-bottom: 0.85rem;">
              <button type="button" class="btn btn-sm btn-full" id="btn-mode-upload" style="background: var(--blue-600); color: white; border-color: var(--blue-600); font-weight: 600;">
                <i data-lucide="upload" style="width: 14px; height: 14px; margin-right: 4px;"></i> Custom Upload
              </button>
              <button type="button" class="btn btn-secondary btn-sm btn-full" id="btn-mode-catalog" style="font-weight: 500;">
                <i data-lucide="database" style="width: 14px; height: 14px; margin-right: 4px;"></i> Catalog Scene
              </button>
            </div>

            <!-- Custom Upload Container -->
            <div id="sar-upload-section">
              <div id="sar-dropzone" style="border: 2px dashed var(--border-strong); border-radius: 6px; padding: 1.25rem 1rem; text-align: center; background: var(--ivory-50); cursor: pointer; transition: all 0.2s ease;">
                <input type="file" id="sar-file-input" accept=".png,.jpg,.jpeg,.tif,.tiff,.geotiff" style="display: none;">
                <i data-lucide="cloud-upload" style="width: 28px; height: 28px; color: var(--blue-600); margin: 0 auto 0.5rem auto; display: block;"></i>
                <div style="font-size: 0.85rem; font-weight: 600; color: var(--blue-900);">Click to browse or drop SAR image</div>
                <div style="font-size: 0.72rem; color: var(--blue-700); margin-top: 0.25rem;">Supported: GeoTIFF (.tif), PNG, JPG (up to 100MB)</div>
              </div>

              <!-- Uploaded File Preview Banner -->
              <div id="sar-file-preview-bar" style="display: none; align-items: center; justify-content: space-between; margin-top: 0.6rem; padding: 0.5rem 0.75rem; background: var(--ivory-200); border-radius: 4px; border: 1px solid var(--border-medium);">
                <div style="display: flex; align-items: center; gap: 0.5rem; overflow: hidden;">
                  <img id="sar-preview-thumb" src="" alt="Thumbnail" style="width: 32px; height: 32px; object-fit: cover; border-radius: 3px; display: none; border: 1px solid var(--border-medium);">
                  <div style="overflow: hidden;">
                    <div id="sar-file-name" style="font-family: var(--font-mono); font-size: 0.78rem; font-weight: 700; color: var(--blue-900); white-space: nowrap; text-overflow: ellipsis; overflow: hidden;">filename.tif</div>
                    <div id="sar-file-size" style="font-size: 0.70rem; color: var(--blue-700);">0.0 MB</div>
                  </div>
                </div>
                <button type="button" id="btn-clear-upload" class="btn btn-secondary btn-sm" style="padding: 0.2rem 0.45rem; font-size: 0.7rem;">Clear</button>
              </div>
            </div>

            <!-- Catalog Scene Container -->
            <div id="sar-catalog-section" style="display: none;">
              <div class="form-group" style="margin-bottom: 0.85rem;">
                <label class="form-label">Satellite Target Scene</label>
                <select id="select-sar-scene" class="form-select">
                  ${OceanTraceData.sarScenes.map(s => `
                    <option value="${s.id}">${s.name} (${s.id.substring(0, 24)}...)</option>
                  `).join('')}
                </select>
              </div>
            </div>

            <!-- Advanced Tuning Controls -->
            <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid var(--border-subtle);">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                <label class="form-label" style="margin-bottom: 0;">Segmentation Threshold</label>
                <span id="threshold-val-display" style="font-family: var(--font-mono); font-size: 0.75rem; font-weight: 700; color: var(--coral-600);">0.50</span>
              </div>
              <input type="range" id="input-threshold" min="0.10" max="0.90" step="0.05" value="0.50" style="width: 100%; accent-color: var(--coral-500); cursor: pointer;">
              <div style="display: flex; justify-content: space-between; font-size: 0.68rem; color: var(--blue-700); margin-top: 2px;">
                <span>0.10 (High Sensitivity)</span>
                <span>0.50 (Standard)</span>
                <span>0.90 (High Precision)</span>
              </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; margin-top: 0.65rem;">
              <div class="form-group" style="margin-bottom: 0;">
                <label class="form-label">Preprocessing</label>
                <select id="select-norm-method" class="form-select">
                  <option value="percentile" selected>Robust Percentile (2-98%)</option>
                  <option value="minmax">Min-Max Scaling</option>
                  <option value="standard">Standard Z-Score</option>
                </select>
              </div>
              <div class="form-group" style="margin-bottom: 0;">
                <label class="form-label">Inference Mode</label>
                <select id="select-inference-mode" class="form-select">
                  <option value="tiled" selected>Tiled Overlap (512px)</option>
                  <option value="direct">Single Chip (256px)</option>
                </select>
              </div>
            </div>

            <!-- Inference Submission Trigger -->
            <button id="btn-run-inference" class="btn btn-primary btn-full" style="margin-top: 0.85rem;">
              <i data-lucide="satellite" style="width: 16px; height: 16px;"></i>
              Execute U-Net Segmentation
            </button>

            <!-- Loading Progress Indicator -->
            <div id="inference-progress" style="display: none; margin-top: 0.6rem; font-size: 0.76rem; color: var(--blue-700); text-align: center;">
              <div style="height: 4px; background: var(--ivory-300); border-radius: 2px; overflow: hidden; margin-bottom: 4px;">
                <div style="height: 100%; width: 100%; background: var(--coral-500); animation: pulse-ring 1s infinite;"></div>
              </div>
              <span id="inference-progress-label">Executing ResNet34 U-Net neural inference on SAR backscatter...</span>
            </div>

            <!-- Error Notification Banner -->
            <div id="inference-error-banner" style="display: none; margin-top: 0.6rem; padding: 0.5rem 0.75rem; background: var(--coral-100); border-left: 3px solid var(--coral-600); border-radius: 3px; font-size: 0.75rem; color: var(--coral-600);">
              <i data-lucide="alert-triangle" style="width: 14px; height: 14px; display: inline; vertical-align: -2px; margin-right: 4px;"></i>
              <span id="inference-error-msg">Failed to connect to backend server.</span>
            </div>
            <!-- Inference Results & Visualizer Container -->
            <div id="inference-results-card" class="card" style="display: none; margin-top: 1rem; border-color: var(--coral-500); background: var(--ivory-100);">
              <div class="card-header" style="margin-bottom: 0.5rem;">
                <div>
                  <h4 class="card-title" style="color: var(--blue-900); font-size: 0.95rem;">U-Net Segmentation Results</h4>
                  <p class="card-subtitle" id="inference-time-label">Completed in -- ms</p>
                </div>
                <span id="prediction-verdict-badge" class="status-pill coral">
                  Spill Detected
                </span>
              </div>

              <!-- Metrics Summary Grid -->
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-bottom: 0.75rem;">
                <div class="meta-field" style="background: var(--ivory-50); padding: 0.4rem; border-radius: 4px; border: 1px solid var(--border-subtle);">
                  <span class="meta-label">Spill Coverage</span>
                  <span id="result-coverage-val" class="meta-value" style="color: var(--coral-600); font-size: 0.95rem;">-- %</span>
                </div>
                <div class="meta-field" style="background: var(--ivory-50); padding: 0.4rem; border-radius: 4px; border: 1px solid var(--border-subtle);">
                  <span class="meta-label">Mean Confidence</span>
                  <span id="result-conf-val" class="meta-value" style="color: var(--blue-700); font-size: 0.95rem;">-- %</span>
                </div>
                <div class="meta-field" style="background: var(--ivory-50); padding: 0.4rem; border-radius: 4px; border: 1px solid var(--border-subtle);">
                  <span class="meta-label">Pixel Dimensions</span>
                  <span id="result-dim-val" class="meta-value" style="font-size: 0.8rem;">-- × --</span>
                </div>
                <div class="meta-field" style="background: var(--ivory-50); padding: 0.4rem; border-radius: 4px; border: 1px solid var(--border-subtle);">
                  <span class="meta-label">Inference Mode</span>
                  <span id="result-mode-val" class="meta-value" style="font-size: 0.8rem;">Tiled U-Net</span>
                </div>
              </div>

              <!-- Visual View Switcher (Overlay vs Mask vs Original) -->
              <div style="margin-bottom: 0.5rem;">
                <div style="display: flex; gap: 0.25rem; background: var(--ivory-200); padding: 0.2rem; border-radius: 4px; margin-bottom: 0.4rem;">
                  <button type="button" class="btn btn-sm btn-full active" id="btn-view-overlay" style="padding: 0.2rem 0.4rem; font-size: 0.72rem; background: var(--blue-600); color: white;">3-Panel Overlay</button>
                  <button type="button" class="btn btn-secondary btn-sm btn-full" id="btn-view-mask" style="padding: 0.2rem 0.4rem; font-size: 0.72rem;">Binary Mask</button>
                  <button type="button" class="btn btn-secondary btn-sm btn-full" id="btn-view-original" style="padding: 0.2rem 0.4rem; font-size: 0.72rem;">Original SAR</button>
                </div>
                <div style="position: relative; border-radius: 4px; overflow: hidden; border: 1px solid var(--border-medium); background: #000; min-height: 180px; display: flex; align-items: center; justify-content: center;">
                  <img id="prediction-result-img" src="" alt="Prediction Result" style="width: 100%; height: auto; max-height: 240px; object-fit: contain; display: block;">
                </div>
              </div>
            </div>

            <!-- Model Benchmark Performance Card (Read-Only Established Test Metrics) -->
            <div class="card" style="margin-top: 1rem; background: var(--ivory-50); border: 1px solid var(--border-subtle);">
              <div class="card-header" style="margin-bottom: 0.5rem;">
                <div>
                  <h4 class="card-title" style="font-size: 0.88rem; color: var(--blue-900);">Model Evaluation Benchmark</h4>
                  <p class="card-subtitle" style="font-size: 0.68rem;">Established test set validation metrics (ResNet34 U-Net)</p>
                </div>
                <span class="status-pill" style="background: var(--blue-100); color: var(--blue-700); font-size: 0.68rem; padding: 0.15rem 0.4rem;">
                  Ground Truth
                </span>
              </div>
              <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.35rem; text-align: center;">
                <div style="padding: 0.35rem 0.2rem; background: var(--ivory-200); border-radius: 4px;">
                  <div style="font-size: 0.65rem; color: var(--blue-700); text-transform: uppercase; font-weight: 600;">Precision</div>
                  <div style="font-family: var(--font-mono); font-weight: 700; color: var(--blue-900); font-size: 0.82rem;">87.76%</div>
                </div>
                <div style="padding: 0.35rem 0.2rem; background: var(--ivory-200); border-radius: 4px;">
                  <div style="font-size: 0.65rem; color: var(--blue-700); text-transform: uppercase; font-weight: 600;">Recall</div>
                  <div style="font-family: var(--font-mono); font-weight: 700; color: var(--blue-900); font-size: 0.82rem;">89.40%</div>
                </div>
                <div style="padding: 0.35rem 0.2rem; background: var(--ivory-200); border-radius: 4px;">
                  <div style="font-size: 0.65rem; color: var(--blue-700); text-transform: uppercase; font-weight: 600;">F1-Score</div>
                  <div style="font-family: var(--font-mono); font-weight: 700; color: var(--coral-600); font-size: 0.82rem;">88.57%</div>
                </div>
                <div style="padding: 0.35rem 0.2rem; background: var(--ivory-200); border-radius: 4px;">
                  <div style="font-size: 0.65rem; color: var(--blue-700); text-transform: uppercase; font-weight: 600;">Global Dice</div>
                  <div style="font-family: var(--font-mono); font-weight: 700; color: var(--coral-600); font-size: 0.82rem;">88.57%</div>
                </div>
              </div>
              <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.35rem; text-align: center; margin-top: 0.35rem;">
                <div style="padding: 0.35rem 0.2rem; background: var(--ivory-200); border-radius: 4px;">
                  <div style="font-size: 0.65rem; color: var(--blue-700); text-transform: uppercase; font-weight: 600;">Mean Dice</div>
                  <div style="font-family: var(--font-mono); font-weight: 700; color: var(--blue-900); font-size: 0.82rem;">82.70%</div>
                </div>
                <div style="padding: 0.35rem 0.2rem; background: var(--ivory-200); border-radius: 4px;">
                  <div style="font-size: 0.65rem; color: var(--blue-700); text-transform: uppercase; font-weight: 600;">Global IoU</div>
                  <div style="font-family: var(--font-mono); font-weight: 700; color: var(--blue-900); font-size: 0.82rem;">79.49%</div>
                </div>
                <div style="padding: 0.35rem 0.2rem; background: var(--ivory-200); border-radius: 4px;">
                  <div style="font-size: 0.65rem; color: var(--blue-700); text-transform: uppercase; font-weight: 600;">Mean IoU</div>
                  <div style="font-family: var(--font-mono); font-weight: 700; color: var(--blue-900); font-size: 0.82rem;">73.27%</div>
                </div>
              </div>
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

    // AIS Vessel Layer Group
    this.aisLayerGroup = L.layerGroup().addTo(this.map);
    this.loadAndRenderAISVessels();
  },

  async loadAndRenderAISVessels() {
    if (!this.aisLayerGroup) return;
    this.aisLayerGroup.clearLayers();

    try {
      const vessels = await OceanTraceApi.getAISVessels();
      vessels.forEach(v => {
        const isDark = v.ais_status && v.ais_status.includes('Dark');
        const markerColor = isDark ? '#EF8557' : '#226192';

        // Render vessel position marker
        const shipIcon = L.divIcon({
          className: 'custom-ship-marker',
          html: `
            <div style="width: 14px; height: 14px; border-radius: 3px; background: ${markerColor}; border: 1.5px solid white; transform: rotate(${v.heading_deg}deg); box-shadow: 0 1px 4px rgba(0,0,0,0.3);">
            </div>
          `,
          iconSize: [14, 14],
          iconAnchor: [7, 7]
        });

        const marker = L.marker([v.latitude, v.longitude], { icon: shipIcon });
        marker.bindPopup(`
          <div style="font-family: var(--font-sans); padding: 4px; min-width: 180px;">
            <div style="font-weight: 700; color: var(--blue-900); font-size: 13px;">${v.vessel_name}</div>
            <div style="font-size: 11px; color: var(--blue-700);">${v.vessel_type} · ${v.flag}</div>
            <div style="font-family: var(--font-mono); font-size: 10px; margin-top: 4px; line-height: 1.4;">
              • MMSI: <strong>${v.mmsi}</strong><br>
              • Speed: <strong>${v.speed_knots} kn</strong> @ ${v.heading_deg}°<br>
              • Status: <strong style="color: ${isDark ? 'var(--coral-600)' : '#137333'};">${v.ais_status}</strong>
            </div>
          </div>
        `);
        this.aisLayerGroup.addLayer(marker);

        // Render historical movement tracks if available
        if (v.trajectory && v.trajectory.length > 1) {
          const trackCoords = v.trajectory.map(pt => [pt.latitude, pt.longitude]);
          const trackLine = L.polyline(trackCoords, {
            color: markerColor,
            weight: 1.5,
            opacity: 0.65,
            dashArray: isDark ? '4, 4' : null
          });
          trackLine.bindTooltip(`${v.vessel_name} Track`, { permanent: false });
          this.aisLayerGroup.addLayer(trackLine);
        }
      });
    } catch (e) {
      console.warn("Failed to load AIS vessels on map:", e);
    }
  },

  uploadedFile: null,
  currentResult: null,

  bindEvents() {
    // Mode toggling (Upload vs Catalog)
    const btnUploadMode = document.getElementById('btn-mode-upload');
    const btnCatalogMode = document.getElementById('btn-mode-catalog');
    const uploadSec = document.getElementById('sar-upload-section');
    const catalogSec = document.getElementById('sar-catalog-section');

    if (btnUploadMode && btnCatalogMode) {
      btnUploadMode.addEventListener('click', () => {
        btnUploadMode.style.background = 'var(--blue-600)';
        btnUploadMode.style.color = 'white';
        btnUploadMode.style.borderColor = 'var(--blue-600)';
        btnCatalogMode.style.background = '';
        btnCatalogMode.style.color = '';
        btnCatalogMode.style.borderColor = '';
        uploadSec.style.display = 'block';
        catalogSec.style.display = 'none';
      });

      btnCatalogMode.addEventListener('click', () => {
        btnCatalogMode.style.background = 'var(--blue-600)';
        btnCatalogMode.style.color = 'white';
        btnCatalogMode.style.borderColor = 'var(--blue-600)';
        btnUploadMode.style.background = '';
        btnUploadMode.style.color = '';
        btnUploadMode.style.borderColor = '';
        uploadSec.style.display = 'none';
        catalogSec.style.display = 'block';
      });
    }

    // Drag and drop & file selection
    const dropzone = document.getElementById('sar-dropzone');
    const fileInput = document.getElementById('sar-file-input');
    const previewBar = document.getElementById('sar-file-preview-bar');
    const previewThumb = document.getElementById('sar-preview-thumb');
    const fileNameEl = document.getElementById('sar-file-name');
    const fileSizeEl = document.getElementById('sar-file-size');
    const clearBtn = document.getElementById('btn-clear-upload');

    if (dropzone && fileInput) {
      dropzone.addEventListener('click', () => fileInput.click());

      dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.style.borderColor = 'var(--coral-500)';
        dropzone.style.background = 'var(--coral-50)';
      });

      dropzone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropzone.style.borderColor = 'var(--border-strong)';
        dropzone.style.background = 'var(--ivory-50)';
      });

      dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.style.borderColor = 'var(--border-strong)';
        dropzone.style.background = 'var(--ivory-50)';
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
          this.handleFileSelected(e.dataTransfer.files[0]);
        }
      });

      fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
          this.handleFileSelected(e.target.files[0]);
        }
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.uploadedFile = null;
        if (fileInput) fileInput.value = '';
        if (previewBar) previewBar.style.display = 'none';
        if (dropzone) dropzone.style.display = 'block';
        if (previewThumb) { previewThumb.src = ''; previewThumb.style.display = 'none'; }
      });
    }

    // Threshold slider
    const threshInput = document.getElementById('input-threshold');
    const threshDisplay = document.getElementById('threshold-val-display');
    if (threshInput && threshDisplay) {
      threshInput.addEventListener('input', (e) => {
        threshDisplay.textContent = parseFloat(e.target.value).toFixed(2);
      });
    }

    // Result view tabs (Overlay / Mask / Original)
    const btnViewOverlay = document.getElementById('btn-view-overlay');
    const btnViewMask = document.getElementById('btn-view-mask');
    const btnViewOrig = document.getElementById('btn-view-original');
    const resultImg = document.getElementById('prediction-result-img');

    const updateViewTabs = (activeBtn, url) => {
      [btnViewOverlay, btnViewMask, btnViewOrig].forEach(btn => {
        if (!btn) return;
        btn.classList.remove('active');
        btn.style.background = '';
        btn.style.color = '';
      });
      activeBtn.classList.add('active');
      activeBtn.style.background = 'var(--blue-600)';
      activeBtn.style.color = 'white';
      if (resultImg && url) {
        resultImg.src = url;
      }
    };

    if (btnViewOverlay && btnViewMask && btnViewOrig) {
      btnViewOverlay.addEventListener('click', () => {
        if (this.currentResult) {
          updateViewTabs(btnViewOverlay, OceanTraceApi.resolveAssetUrl(this.currentResult.overlay_url));
        }
      });
      btnViewMask.addEventListener('click', () => {
        if (this.currentResult) {
          updateViewTabs(btnViewMask, OceanTraceApi.resolveAssetUrl(this.currentResult.mask_url));
        }
      });
      btnViewOrig.addEventListener('click', () => {
        if (this.currentResult) {
          updateViewTabs(btnViewOrig, OceanTraceApi.resolveAssetUrl(this.currentResult.original_url));
        }
      });
    }

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
      runBtn.addEventListener('click', async () => {
        await this.executeInference();
      });
    }

    // AIS toggle button
    const btnToggleAis = document.getElementById('btn-toggle-ais');
    if (btnToggleAis) {
      btnToggleAis.addEventListener('click', () => {
        if (!this.map || !this.aisLayerGroup) return;
        if (this.map.hasLayer(this.aisLayerGroup)) {
          this.map.removeLayer(this.aisLayerGroup);
          btnToggleAis.classList.remove('active');
        } else {
          this.map.addLayer(this.aisLayerGroup);
          btnToggleAis.classList.add('active');
        }
      });
    }

    // SAR footprint toggle button
    const btnToggleSar = document.getElementById('btn-toggle-sar');
    if (btnToggleSar) {
      btnToggleSar.addEventListener('click', () => {
        if (!this.map || !this.sarLayer) return;
        if (this.map.hasLayer(this.sarLayer)) {
          this.map.removeLayer(this.sarLayer);
          btnToggleSar.classList.remove('active');
        } else {
          this.map.addLayer(this.sarLayer);
          btnToggleSar.classList.add('active');
        }
      });
    }

    // Slick toggle button
    const btnToggleSlick = document.getElementById('btn-toggle-slick');
    if (btnToggleSlick) {
      btnToggleSlick.addEventListener('click', () => {
        if (!this.map || !this.spillLayer) return;
        if (this.map.hasLayer(this.spillLayer)) {
          this.map.removeLayer(this.spillLayer);
          btnToggleSlick.classList.remove('active');
        } else {
          this.map.addLayer(this.spillLayer);
          btnToggleSlick.classList.add('active');
        }
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
  },

  handleFileSelected(file) {
    const validExtensions = ['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.geotiff'];
    const fileName = file.name.toLowerCase();
    const isValid = validExtensions.some(ext => fileName.endsWith(ext));

    const errBanner = document.getElementById('inference-error-banner');
    const errMsg = document.getElementById('inference-error-msg');

    if (!isValid) {
      if (errBanner && errMsg) {
        errMsg.textContent = `Unsupported file type: ${file.name}. Please select a PNG, JPG, or GeoTIFF.`;
        errBanner.style.display = 'block';
      }
      return;
    }

    // Check size limit (100MB)
    if (file.size > 100 * 1024 * 1024) {
      if (errBanner && errMsg) {
        errMsg.textContent = `File size exceeds 100MB limit (${(file.size / (1024*1024)).toFixed(1)} MB).`;
        errBanner.style.display = 'block';
      }
      return;
    }

    if (errBanner) errBanner.style.display = 'none';
    this.uploadedFile = file;

    const previewBar = document.getElementById('sar-file-preview-bar');
    const dropzone = document.getElementById('sar-dropzone');
    const fileNameEl = document.getElementById('sar-file-name');
    const fileSizeEl = document.getElementById('sar-file-size');
    const previewThumb = document.getElementById('sar-preview-thumb');

    if (fileNameEl) fileNameEl.textContent = file.name;
    if (fileSizeEl) fileSizeEl.textContent = `${(file.size / (1024 * 1024)).toFixed(2)} MB · ${file.type || 'image/sar'}`;
    if (dropzone) dropzone.style.display = 'none';
    if (previewBar) previewBar.style.display = 'flex';

    // Show image preview thumbnail if browser-renderable
    if (file.type.startsWith('image/') && !fileName.endsWith('.tif') && !fileName.endsWith('.tiff') && !fileName.endsWith('.geotiff')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        if (previewThumb) {
          previewThumb.src = e.target.result;
          previewThumb.style.display = 'block';
        }
      };
      reader.readAsDataURL(file);
    } else {
      if (previewThumb) previewThumb.style.display = 'none';
    }
  },

  async executeInference() {
    const runBtn = document.getElementById('btn-run-inference');
    const prog = document.getElementById('inference-progress');
    const errBanner = document.getElementById('inference-error-banner');
    const errMsg = document.getElementById('inference-error-msg');
    const resultsCard = document.getElementById('inference-results-card');

    if (errBanner) errBanner.style.display = 'none';

    // Collect parameters
    const thresholdInput = document.getElementById('input-threshold');
    const threshold = thresholdInput ? parseFloat(thresholdInput.value) : 0.5;
    const normSelect = document.getElementById('select-norm-method');
    const normMethod = normSelect ? normSelect.value : 'percentile';
    const modeSelect = document.getElementById('select-inference-mode');
    const inferenceMode = modeSelect ? modeSelect.value : 'tiled';

    let fileToAnalyze = this.uploadedFile;

    // If no custom file was uploaded, create a synthetic SAR sample chip
    if (!fileToAnalyze) {
      // Create a 256x256 synthetic SAR canvas chip for demo simulation
      const canvas = document.createElement('canvas');
      canvas.width = 256;
      canvas.height = 256;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#1B4E78';
      ctx.fillRect(0, 0, 256, 256);
      // Dark slick streak
      ctx.fillStyle = '#0F293F';
      ctx.beginPath();
      ctx.ellipse(128, 128, 50, 20, Math.PI / 4, 0, 2 * Math.PI);
      ctx.fill();

      fileToAnalyze = await new Promise(resolve => {
        canvas.toBlob(blob => {
          resolve(new File([blob], 'catalog_scene_chip.png', { type: 'image/png' }));
        }, 'image/png');
      });
    }

    try {
      runBtn.disabled = true;
      if (prog) prog.style.display = 'block';

      const options = {
        threshold: threshold,
        normMethod: normMethod,
        tileSize: inferenceMode === 'tiled' ? 512 : 256,
        overlap: 64
      };

      const result = await OceanTraceApi.predictSpill(fileToAnalyze, options);
      this.currentResult = result;

      // Populate results card
      if (resultsCard) {
        resultsCard.style.display = 'block';

        const timeLabel = document.getElementById('inference-time-label');
        if (timeLabel) timeLabel.textContent = `Completed in ${result.processing_time_ms.toFixed(1)} ms · ID: ${result.prediction_id.substring(0, 8)}`;

        const verdictBadge = document.getElementById('prediction-verdict-badge');
        if (verdictBadge) {
          verdictBadge.textContent = result.spill_detected ? 'Spill Detected' : 'No Spill Detected';
          verdictBadge.className = result.spill_detected ? 'status-pill coral' : 'status-pill live';
        }

        const covVal = document.getElementById('result-coverage-val');
        if (covVal) covVal.textContent = `${result.oil_spill_coverage_pct.toFixed(2)} %`;

        const confVal = document.getElementById('result-conf-val');
        if (confVal) {
          confVal.textContent = result.mean_confidence_pct != null ? `${result.mean_confidence_pct.toFixed(1)} %` : 'N/A';
        }

        const dimVal = document.getElementById('result-dim-val');
        if (dimVal) dimVal.textContent = `${result.dimensions.width} × ${result.dimensions.height} px`;

        const modeVal = document.getElementById('result-mode-val');
        if (modeVal) modeVal.textContent = result.metadata.mode || 'U-Net';

        // Set default image to overlay
        const resultImg = document.getElementById('prediction-result-img');
        if (resultImg) {
          resultImg.src = OceanTraceApi.resolveAssetUrl(result.overlay_url);
        }

        // Reset visual tabs
        const btnViewOverlay = document.getElementById('btn-view-overlay');
        const btnViewMask = document.getElementById('btn-view-mask');
        const btnViewOrig = document.getElementById('btn-view-original');
        if (btnViewOverlay && btnViewMask && btnViewOrig) {
          btnViewOverlay.classList.add('active');
          btnViewOverlay.style.background = 'var(--blue-600)';
          btnViewOverlay.style.color = 'white';
          btnViewMask.classList.remove('active');
          btnViewMask.style.background = '';
          btnViewMask.style.color = '';
          btnViewOrig.classList.remove('active');
          btnViewOrig.style.background = '';
          btnViewOrig.style.color = '';
        }
      }

      // If spill detected, add to OceanTraceData incidents list dynamically
      if (result.spill_detected) {
        const newIncId = `INC-2026-${result.prediction_id.substring(0, 4).toUpperCase()}`;
        OceanTraceData.incidents[newIncId] = {
          id: newIncId,
          name: `U-Net Detection ${newIncId}`,
          locationName: 'Detected SAR Target Area',
          severity: result.oil_spill_coverage_pct > 5 ? 'High' : 'Medium',
          centroid: [24.812, 57.240],
          areaKm2: parseFloat((result.oil_spill_coverage_pct * 0.85).toFixed(2)),
          perimeterKm: parseFloat((result.oil_spill_coverage_pct * 1.4 + 2.1).toFixed(2)),
          modelConfidence: result.mean_confidence_pct != null ? Math.round(result.mean_confidence_pct) : 88,
          minBackscatterDb: 22.4,
          status: 'Under AI Forensics Review'
        };

        // Query backend spatial-temporal correlation engine
        try {
          const candidates = await OceanTraceApi.correlateVesselsWithSpill(
            24.812, 57.240, new Date().toISOString(), 50.0
          );
          if (candidates && candidates.length > 0) {
            console.log(`[OceanTrace] Correlated ${candidates.length} candidate vessels for ${newIncId}`);
          }
        } catch (corrErr) {
          console.warn("[OceanTrace] Correlation query error:", corrErr);
        }
      }

    } catch (err) {
      console.error('[OceanTrace] Inference failed:', err);
      if (errBanner && errMsg) {
        errMsg.textContent = err.message || 'Inference execution failed.';
        errBanner.style.display = 'block';
      }
    } finally {
      runBtn.disabled = false;
      if (prog) prog.style.display = 'none';
      if (window.lucide) lucide.createIcons();
    }
  }
};
