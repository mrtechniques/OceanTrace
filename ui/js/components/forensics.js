/**
 * Drift & Hindcast Forensics Component (Page 2)
 */
const ForensicsComponent = {
  map: null,
  driftTrackLayer: null,
  driftMarker: null,
  driftCircle: null,
  isPlaying: false,
  playTimer: null,
  currentStepIndex: 0,

  render() {
    const inc = OceanTraceData.incidents[OceanTraceData.activeIncidentId];
    const drift = OceanTraceData.driftSimulation;

    return `
      <div class="split-view">
        <!-- Main Interactive Drift Map -->
        <div class="split-map-pane">
          <!-- Forensics Header Bar inside Map -->
          <div class="map-toolbar" style="width: auto; right: 1rem; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              <span style="font-family: var(--font-mono); font-size: 0.8rem; font-weight: 700; color: var(--blue-900);">
                INCIDENT: ${inc.id}
              </span>
              <span class="status-pill coral">Backward Lagrangian Hindcast</span>
            </div>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <span style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--blue-700);">
                Metocean: ERA5 Wind + CMEMS Currents
              </span>
            </div>
          </div>

          <!-- Leaflet Map Canvas -->
          <div id="forensics-map" class="map-canvas"></div>

          <!-- Interactive Time-Scrubber Card Overlay -->
          <div class="timeline-scrubber-card">
            <div class="timeline-header">
              <div style="display: flex; align-items: center; gap: 0.75rem;">
                <button id="btn-play-drift" class="btn btn-secondary btn-sm" style="padding: 0.4rem 0.75rem;">
                  <i id="play-icon" data-lucide="play" style="width: 14px; height: 14px;"></i>
                  <span id="play-text">Simulate</span>
                </button>
                <div style="display: flex; flex-direction: column;">
                  <span id="current-step-label" style="font-family: var(--font-serif); font-size: 0.95rem; font-weight: 600; color: var(--blue-900);">
                    ${drift.timesteps[0].label}
                  </span>
                  <span id="current-step-time" style="font-family: var(--font-mono); font-size: 0.76rem; color: var(--coral-600); font-weight: 600;">
                    ${drift.timesteps[0].timeUtc}
                  </span>
                </div>
              </div>

              <div style="display: flex; align-items: center; gap: 1.5rem;">
                <div style="text-align: right;">
                  <span style="font-size: 0.68rem; text-transform: uppercase; color: var(--blue-700); font-weight: 600;">Dispersion Centroid</span>
                  <div id="step-coordinates" style="font-family: var(--font-mono); font-size: 0.82rem; font-weight: 600; color: var(--blue-900);">
                    ${drift.timesteps[0].lat.toFixed(3)}° N, ${drift.timesteps[0].lon.toFixed(3)}° E
                  </div>
                </div>
                <div style="text-align: right;">
                  <span style="font-size: 0.68rem; text-transform: uppercase; color: var(--blue-700); font-weight: 600;">Slick Footprint</span>
                  <div id="step-area" style="font-family: var(--font-mono); font-size: 0.82rem; font-weight: 600; color: var(--coral-600);">
                    ${drift.timesteps[0].areaKm2} km²
                  </div>
                </div>
              </div>
            </div>

            <!-- Slider Range Control -->
            <div class="timeline-slider-wrapper">
              <span style="font-family: var(--font-mono); font-size: 0.74rem; font-weight: 600; color: var(--coral-600);">T-14h (Discharge)</span>
              <input type="range" id="drift-slider" class="timeline-slider" min="0" max="${drift.timesteps.length - 1}" step="1" value="0">
              <span style="font-family: var(--font-mono); font-size: 0.74rem; font-weight: 600; color: var(--blue-700);">T-0h (SAR Detection)</span>
            </div>
          </div>
        </div>

        <!-- Right Forensics Dossier Panel -->
        <div class="split-side-pane">
          <!-- Spill Physical Characteristics Card -->
          <div class="card">
            <div class="card-header">
              <div>
                <h3 class="card-title">Slick Morphometry</h3>
                <p class="card-subtitle">CRS-Aware Geodesic Properties</p>
              </div>
              <span style="font-family: var(--font-mono); font-size: 0.72rem; color: var(--blue-600); font-weight: 600;">
                WGS84 / EPSG:4326
              </span>
            </div>

            <div class="incident-meta-grid" style="border-top: none; padding-top: 0;">
              <div class="meta-field">
                <span class="meta-label">Geodesic Area</span>
                <span class="meta-value" style="color: var(--coral-600);">${inc.areaKm2} km²</span>
              </div>
              <div class="meta-field">
                <span class="meta-label">Perimeter</span>
                <span class="meta-value">${inc.perimeterKm} km</span>
              </div>
              <div class="meta-field">
                <span class="meta-label">Elongation Ratio</span>
                <span class="meta-value">${inc.elongation}</span>
              </div>
              <div class="meta-field">
                <span class="meta-label">Circularity</span>
                <span class="meta-value">${inc.circularity}</span>
              </div>
              <div class="meta-field">
                <span class="meta-label">Peak Low Backscatter</span>
                <span class="meta-value">${inc.minBackscatterDb} dB</span>
              </div>
              <div class="meta-field">
                <span class="meta-label">Ocean Clutter σ⁰</span>
                <span class="meta-value">${inc.meanSeaBackscatterDb} dB</span>
              </div>
            </div>
          </div>

          <!-- Metocean & Hydrodynamic Forcing Card -->
          <div class="card">
            <div class="card-header">
              <div>
                <h3 class="card-title">Metocean Forcing</h3>
                <p class="card-subtitle">Copernicus CMEMS & ERA5 Reanalysis</p>
              </div>
              <i data-lucide="wind" style="width: 18px; height: 18px; color: var(--blue-600);"></i>
            </div>

            <div style="display: flex; flex-direction: column; gap: 0.65rem;">
              <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 0.5rem; border-bottom: 1px dashed var(--border-subtle);">
                <span style="font-size: 0.78rem; color: var(--blue-700);">Surface Wind (10m)</span>
                <span style="font-family: var(--font-mono); font-weight: 600; font-size: 0.82rem; color: var(--blue-900);">${drift.metocean.windVector}</span>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 0.5rem; border-bottom: 1px dashed var(--border-subtle);">
                <span style="font-size: 0.78rem; color: var(--blue-700);">Surface Ocean Current</span>
                <span style="font-family: var(--font-mono); font-weight: 600; font-size: 0.82rem; color: var(--blue-900);">${drift.metocean.currentVector}</span>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 0.5rem; border-bottom: 1px dashed var(--border-subtle);">
                <span style="font-size: 0.78rem; color: var(--blue-700);">Sea Surface Temperature</span>
                <span style="font-family: var(--font-mono); font-weight: 600; font-size: 0.82rem; color: var(--blue-900);">${drift.metocean.seaTemp}</span>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 0.78rem; color: var(--blue-700);">Significant Wave Height</span>
                <span style="font-family: var(--font-mono); font-weight: 600; font-size: 0.82rem; color: var(--blue-900);">${drift.metocean.waveHeight}</span>
              </div>
            </div>
          </div>

          <!-- Culprit Attributability CTA -->
          <div class="card" style="background-color: var(--ivory-200); border-color: var(--blue-600);">
            <div style="display: flex; align-items: flex-start; gap: 0.75rem; margin-bottom: 1rem;">
              <div style="background: var(--blue-100); color: var(--blue-600); padding: 0.5rem; border-radius: 6px;">
                <i data-lucide="compass" style="width: 20px; height: 20px;"></i>
              </div>
              <div>
                <h4 style="font-family: var(--font-serif); font-size: 1.05rem; font-weight: 600; color: var(--blue-900);">
                  Reverse Trajectory Converged
                </h4>
                <p style="font-size: 0.78rem; color: var(--blue-700); margin-top: 0.2rem;">
                  Origin corridor localized at <strong>24.570° N, 56.960° E</strong> between 15:42 and 19:42 UTC. Ready to cross-reference with historical AIS vessel tracking records.
                </p>
              </div>
            </div>

            <button id="btn-goto-attribution" class="btn btn-primary btn-full">
              Correlate AIS Trajectories
              <i data-lucide="arrow-right" style="width: 16px; height: 16px;"></i>
            </button>
          </div>
        </div>
      </div>
    `;
  },

  initMap() {
    const drift = OceanTraceData.driftSimulation;
    const origin = drift.timesteps[0];

    if (this.map) {
      this.map.remove();
    }

    this.map = L.map('forensics-map', {
      zoomControl: true,
      attributionControl: false
    }).setView([24.69, 57.10], 10);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      maxZoom: 18,
      subdomains: 'abcd'
    }).addTo(this.map);

    // Draw Hindcast Trajectory Cone / Polyline
    const pathCoords = drift.timesteps.map(t => [t.lat, t.lon]);
    this.driftTrackLayer = L.polyline(pathCoords, {
      color: '#226192',
      weight: 3,
      dashArray: '5, 5',
      opacity: 0.85
    }).addTo(this.map);

    // Initial marker at current timestep
    this.driftMarker = L.circleMarker([origin.lat, origin.lon], {
      radius: 8,
      fillColor: '#EF8557',
      color: '#FFFFFF',
      weight: 2,
      opacity: 1,
      fillOpacity: 0.9
    }).addTo(this.map);

    this.driftCircle = L.circle([origin.lat, origin.lon], {
      radius: origin.radius,
      fillColor: '#EF8557',
      color: '#EF8557',
      weight: 1.5,
      fillOpacity: 0.25,
      dashArray: '4, 4'
    }).addTo(this.map);

    // Origin Locus Marker (T-14h)
    const releaseStep = drift.timesteps[drift.timesteps.length - 1];
    L.circleMarker([releaseStep.lat, releaseStep.lon], {
      radius: 6,
      fillColor: '#226192',
      color: '#FFFFFF',
      weight: 2,
      fillOpacity: 1
    }).addTo(this.map).bindTooltip('Estimated Spill Release Locus (T-14h)', { permanent: true, direction: 'bottom' });
  },

  updateStep(index) {
    const drift = OceanTraceData.driftSimulation;
    const step = drift.timesteps[index];
    this.currentStepIndex = index;

    document.getElementById('current-step-label').textContent = step.label;
    document.getElementById('current-step-time').textContent = step.timeUtc;
    document.getElementById('step-coordinates').textContent = `${step.lat.toFixed(3)}° N, ${step.lon.toFixed(3)}° E`;
    document.getElementById('step-area').textContent = `${step.areaKm2} km²`;
    document.getElementById('drift-slider').value = index;

    // Update map positions
    if (this.driftMarker && this.driftCircle) {
      this.driftMarker.setLatLng([step.lat, step.lon]);
      this.driftCircle.setLatLng([step.lat, step.lon]);
      this.driftCircle.setRadius(step.radius);
    }
  },

  bindEvents() {
    const slider = document.getElementById('drift-slider');
    if (slider) {
      slider.addEventListener('input', (e) => {
        this.updateStep(parseInt(e.target.value, 10));
      });
    }

    const playBtn = document.getElementById('btn-play-drift');
    if (playBtn) {
      playBtn.addEventListener('click', () => {
        this.togglePlay();
      });
    }

    const gotoBtn = document.getElementById('btn-goto-attribution');
    if (gotoBtn) {
      gotoBtn.addEventListener('click', () => {
        App.navigateTo('attribution');
      });
    }
  },

  togglePlay() {
    const drift = OceanTraceData.driftSimulation;
    if (this.isPlaying) {
      clearInterval(this.playTimer);
      this.isPlaying = false;
      document.getElementById('play-text').textContent = 'Simulate';
    } else {
      this.isPlaying = true;
      document.getElementById('play-text').textContent = 'Pause';
      this.playTimer = setInterval(() => {
        let nextIndex = this.currentStepIndex + 1;
        if (nextIndex >= drift.timesteps.length) {
          nextIndex = 0;
        }
        this.updateStep(nextIndex);
      }, 1000);
    }
  }
};
