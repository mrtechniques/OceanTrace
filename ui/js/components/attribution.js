/**
 * Vessel Attribution Dossier Component (Page 3)
 */
const AttributionComponent = {
  map: null,

  render() {
    const inc = OceanTraceData.incidents[OceanTraceData.activeIncidentId];
    const vessels = OceanTraceData.candidateVessels;
    const culprit = vessels.find(v => v.isCulprit);

    return `
      <div style="flex: 1; display: flex; flex-direction: column; overflow-y: auto; padding: 1.5rem; gap: 1.5rem;">
        <!-- Top Banner / Incident Attribution Context -->
        <div style="display: flex; align-items: center; justify-content: space-between; background: var(--ivory-100); border: 1px solid var(--border-medium); border-radius: 8px; padding: 1.25rem 1.5rem; box-shadow: var(--shadow-sm);">
          <div>
            <div style="display: flex; align-items: center; gap: 0.6rem;">
              <span style="font-family: var(--font-mono); font-size: 0.85rem; font-weight: 700; color: var(--blue-900);">
                INCIDENT ${inc.id}
              </span>
              <span class="status-pill coral">Culprit Identified</span>
              <span style="font-size: 0.78rem; color: var(--blue-700); font-family: var(--font-mono);">
                Gulf of Oman · 24.812° N, 57.240° E
              </span>
            </div>
            <h2 style="font-family: var(--font-serif); font-size: 1.45rem; font-weight: 600; color: var(--blue-900); margin-top: 0.35rem;">
              Spatio-Temporal AIS Trajectory Attribution
            </h2>
            <p style="font-size: 0.82rem; color: var(--blue-700); margin-top: 0.2rem;">
              Correlated 18 commercial vessels against backward Lagrangian drift cone. 1 vessel exhibits anomalous speed deceleration and deliberate AIS transponder blackout during the release window.
            </p>
          </div>

          <div style="display: flex; align-items: center; gap: 0.75rem;">
            <button id="btn-open-dossier" class="btn btn-primary btn-lg">
              <i data-lucide="file-check" style="width: 18px; height: 18px;"></i>
              Export Legal Evidence Dossier (PDF)
            </button>
            <button id="btn-download-geojson" class="btn btn-outline btn-lg">
              <i data-lucide="download" style="width: 18px; height: 18px;"></i>
              GeoJSON Package
            </button>
          </div>
        </div>

        <!-- 2-Column Split: Table on Left (60%), Spatio-Temporal Map on Right (40%) -->
        <div style="display: grid; grid-template-columns: 1.15fr 0.85fr; gap: 1.5rem; min-height: 520px;">
          <!-- Left: Candidate Vessels Table -->
          <div style="display: flex; flex-direction: column; gap: 1rem;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <h3 style="font-family: var(--font-serif); font-size: 1.15rem; font-weight: 600; color: var(--blue-900);">
                Candidate Vessel Correlation Ranking
              </h3>
              <span style="font-size: 0.75rem; color: var(--blue-700); font-family: var(--font-mono);">
                Closest Point of Approach (CPA) ≤ 15.0 nm
              </span>
            </div>

            <div class="table-wrapper">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Vessel Name & Class</th>
                    <th>MMSI / Flag</th>
                    <th>CPA & Time (UTC)</th>
                    <th>AIS Integrity & Speed</th>
                    <th>Score</th>
                  </tr>
                </thead>
                <tbody>
                  ${vessels.map(v => `
                    <tr class="${v.isCulprit ? 'culprit-row' : ''}">
                      <td style="font-family: var(--font-mono); font-weight: 700; color: ${v.isCulprit ? 'var(--coral-600)' : 'var(--blue-900)'};">
                        #${v.rank}
                      </td>
                      <td>
                        <div style="font-weight: 600; font-size: 0.85rem; color: var(--blue-900);">${v.name}</div>
                        <div style="font-size: 0.72rem; color: var(--blue-700);">${v.type} (${v.dwt})</div>
                      </td>
                      <td>
                        <div style="font-family: var(--font-mono); font-size: 0.78rem;">${v.mmsi}</div>
                        <div style="font-size: 0.72rem; color: var(--blue-700);">${v.flag}</div>
                      </td>
                      <td>
                        <div style="font-family: var(--font-mono); font-weight: 600; color: ${v.isCulprit ? 'var(--coral-600)' : 'var(--blue-900)'};">
                          ${v.cpaDistanceNm}
                        </div>
                        <div style="font-size: 0.72rem; color: var(--blue-700); font-family: var(--font-mono);">${v.cpaTimeUtc}</div>
                      </td>
                      <td>
                        <div style="font-size: 0.78rem; font-weight: 600; color: ${v.isCulprit ? 'var(--coral-600)' : '#137333'};">
                          ${v.aisStatus}
                        </div>
                        <div style="font-size: 0.72rem; color: var(--blue-700); font-family: var(--font-mono);">${v.speedProfile}</div>
                      </td>
                      <td>
                        <div style="display: flex; align-items: center;">
                          <div class="confidence-bar-bg">
                            <div class="confidence-bar-fill ${v.isCulprit ? 'coral' : ''}" style="width: ${v.correlationScore}%;"></div>
                          </div>
                          <span style="font-family: var(--font-mono); font-weight: 700; font-size: 0.82rem; color: ${v.isCulprit ? 'var(--coral-600)' : 'var(--blue-900)'};">
                            ${v.correlationScore}%
                          </span>
                        </div>
                        ${v.isCulprit ? `
                          <div style="margin-top: 0.35rem;">
                            <span class="culprit-badge">
                              <i data-lucide="alert-triangle" style="width: 11px; height: 11px;"></i>
                              Primary Culprit
                            </span>
                          </div>
                        ` : ''}
                      </td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>

            <!-- Culprit Detailed Evidence Highlight Card -->
            <div class="card" style="background-color: #FFF9F5; border-color: rgba(239, 133, 87, 0.4);">
              <div style="display: flex; align-items: flex-start; gap: 0.85rem;">
                <div style="background-color: var(--coral-100); color: var(--coral-600); padding: 0.6rem; border-radius: 6px;">
                  <i data-lucide="shield-alert" style="width: 22px; height: 22px;"></i>
                </div>
                <div>
                  <h4 style="font-family: var(--font-serif); font-size: 1.1rem; font-weight: 600; color: var(--blue-900);">
                    Attribution Forensic Assessment: ${culprit.name} (IMO: ${culprit.imo})
                  </h4>
                  <p style="font-size: 0.82rem; color: var(--blue-800); margin-top: 0.3rem; line-height: 1.55;">
                    ${culprit.evidenceSummary}
                  </p>
                  <div style="display: flex; gap: 1.5rem; margin-top: 0.75rem; font-family: var(--font-mono); font-size: 0.75rem; color: var(--blue-700);">
                    <span>• LOA / Beam: <strong>${culprit.length} × ${culprit.beam}</strong></span>
                    <span>• CPA Distance: <strong style="color: var(--coral-600);">${culprit.cpaDistanceNm}</strong></span>
                    <span>• Dark Gap: <strong style="color: var(--coral-600);">${culprit.aisGapDetails}</strong></span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Right: Spatio-Temporal Trajectory Intersection Map -->
          <div style="display: flex; flex-direction: column; gap: 1rem;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <h3 style="font-family: var(--font-serif); font-size: 1.15rem; font-weight: 600; color: var(--blue-900);">
                Trajectory Intersection Corridor
              </h3>
              <span class="status-pill live">
                <span class="pulse-dot"></span> AIS Intersect Confirmed
              </span>
            </div>

            <div class="card" style="padding: 0; overflow: hidden; height: 100%; min-height: 440px; display: flex; flex-direction: column;">
              <div id="attribution-map" style="width: 100%; flex: 1; min-height: 380px;"></div>
              <div style="padding: 0.75rem 1rem; background-color: var(--ivory-100); border-top: 1px solid var(--border-subtle); display: flex; align-items: center; justify-content: space-between; font-family: var(--font-mono); font-size: 0.75rem;">
                <div style="display: flex; align-items: center; gap: 0.85rem;">
                  <span style="display: flex; align-items: center; gap: 0.35rem;">
                    <span style="width: 12px; height: 3px; background-color: var(--coral-500); display: inline-block;"></span>
                    ${culprit.name} Track
                  </span>
                  <span style="display: flex; align-items: center; gap: 0.35rem;">
                    <span style="width: 12px; height: 3px; background-color: var(--blue-600); display: inline-block;"></span>
                    Traffic Separation Route
                  </span>
                </div>
                <span style="color: var(--coral-600); font-weight: 700;">Intersection Point: 24.640° N, 57.045° E</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  },

  initMap() {
    if (this.map) {
      this.map.remove();
    }

    this.map = L.map('attribution-map', {
      zoomControl: true,
      attributionControl: false
    }).setView([24.68, 57.10], 10);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      maxZoom: 18,
      subdomains: 'abcd'
    }).addTo(this.map);

    // Culprit track (intersects the spill release point)
    const culpritCoords = [
      [24.520, 56.880],
      [24.580, 56.960],
      [24.640, 57.045], // Intersection point with release locus
      [24.700, 57.140],
      [24.760, 57.240]
    ];

    L.polyline(culpritCoords, {
      color: '#EF8557',
      weight: 3.5,
      dashArray: '6, 4',
      opacity: 0.95
    }).addTo(this.map).bindTooltip('M/T Ocean Crown (AIS Anomaly Route)', { permanent: false });

    // Normal traffic line (Pacific Voyager)
    const trafficCoords = [
      [24.450, 56.980],
      [24.530, 57.120],
      [24.610, 57.260],
      [24.690, 57.400]
    ];
    L.polyline(trafficCoords, {
      color: '#226192',
      weight: 2,
      opacity: 0.5
    }).addTo(this.map).bindTooltip('Pacific Voyager (Normal Transit)', { permanent: false });

    // Discharge Point Marker
    const dischargeMarker = L.circleMarker([24.640, 57.045], {
      radius: 9,
      fillColor: '#EF8557',
      color: '#FFFFFF',
      weight: 3,
      fillOpacity: 1
    }).addTo(this.map);

    dischargeMarker.bindPopup(`
      <div style="font-family: var(--font-sans); padding: 4px;">
        <div style="font-weight: 700; color: #EF8557; font-size: 13px;">Critical Intersection Locus</div>
        <div style="font-family: var(--font-mono); font-size: 11px; margin-top: 4px; line-height: 1.5;">
          • Location: 24.640° N, 57.045° E<br>
          • Time: 24 Nov 19:15 UTC (T-10h)<br>
          • Vessel: M/T Ocean Crown<br>
          • Speed: 5.1 kn (64% deceleration)<br>
          • Status: AIS transponder blackout
        </div>
      </div>
    `).openPopup();
  },

  bindEvents() {
    const dossierBtn = document.getElementById('btn-open-dossier');
    if (dossierBtn) {
      dossierBtn.addEventListener('click', () => {
        DossierModalComponent.open();
      });
    }

    const geojsonBtn = document.getElementById('btn-download-geojson');
    if (geojsonBtn) {
      geojsonBtn.addEventListener('click', () => {
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(OceanTraceData.incidents['OT-26143-A'], null, 2));
        const downloadAnchor = document.createElement('a');
        downloadAnchor.setAttribute("href", dataStr);
        downloadAnchor.setAttribute("download", "OceanTrace_OT-26143-A_VectorEvidence.geojson");
        document.body.appendChild(downloadAnchor);
        downloadAnchor.click();
        downloadAnchor.remove();
      });
    }
  }
};
