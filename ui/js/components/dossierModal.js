/**
 * Dossier Modal Component (Legal Evidence Dossier Export)
 */
const DossierModalComponent = {
  render() {
    return `
      <div id="dossier-modal" class="modal-backdrop">
        <div class="modal-dialog">
          <div class="modal-header">
            <div style="display: flex; align-items: center; gap: 0.75rem;">
              <div style="background-color: var(--blue-100); color: var(--blue-600); padding: 0.4rem; border-radius: 5px;">
                <i data-lucide="shield-check" style="width: 20px; height: 20px;"></i>
              </div>
              <div>
                <h3 style="font-family: var(--font-serif); font-size: 1.25rem; font-weight: 600; color: var(--blue-900);">
                  Legal Evidence Dossier
                </h3>
                <p style="font-size: 0.75rem; color: var(--blue-700); font-family: var(--font-mono);">
                  Document Ref: OT-DOSSIER-2026-26143-A · Tamper-Evident Record
                </p>
              </div>
            </div>
            <button id="btn-close-modal" class="btn btn-ghost" style="padding: 0.35rem 0.6rem;">
              <i data-lucide="x" style="width: 20px; height: 20px;"></i>
            </button>
          </div>

          <div class="modal-body">
            <div class="dossier-paper" id="dossier-print-content">
              <!-- Dossier Formal Header -->
              <div style="display: flex; justify-content: space-between; border-bottom: 2px solid var(--blue-900); padding-bottom: 1rem; margin-bottom: 1.25rem;">
                <div>
                  <h1 style="font-family: var(--font-serif); font-size: 1.35rem; font-weight: 700; color: var(--blue-900); text-transform: uppercase; letter-spacing: 0.04em;">
                    OceanTrace Maritime Intelligence Agency
                  </h1>
                  <p style="font-size: 0.75rem; color: var(--blue-700); text-transform: uppercase; letter-spacing: 0.08em; margin-top: 0.2rem;">
                    Copernicus Sentinel-1 SAR Oil-Spill Attribution Protocol
                  </p>
                </div>
                <div style="text-align: right; font-family: var(--font-mono); font-size: 0.72rem; color: var(--blue-800);">
                  <div>Date: <strong>25 November 2026</strong></div>
                  <div>Jurisdiction: <strong>International EEZ Waters</strong></div>
                </div>
              </div>

              <!-- Executive Summary -->
              <div style="background-color: var(--ivory-100); border: 1px solid var(--border-medium); border-radius: 6px; padding: 1rem; margin-bottom: 1.25rem;">
                <div style="font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--coral-600); font-weight: 700; margin-bottom: 0.25rem;">
                  Attribution Verdict · 94.2% Confidence
                </div>
                <p style="font-size: 0.84rem; color: var(--blue-900); line-height: 1.5;">
                  Satellite SAR imaging and backward Lagrangian hydrodynamic hindcasting confirm that the 14.82 km² hydrocarbon discharge at 24.812° N, 57.240° E originated from <strong>M/T Ocean Crown (IMO: 9481234, Panama Flag)</strong> on 24 November 2026 at approximately 19:15 UTC. The vessel executed a deliberate transponder blackout accompanied by an unlogged 64% speed reduction.
                </p>
              </div>

              <!-- Metadata Grid -->
              <div class="dossier-grid">
                <div>
                  <h4 style="font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--blue-700); font-weight: 700; margin-bottom: 0.5rem;">
                    1. Satellite SAR Observation
                  </h4>
                  <table style="width: 100%; font-size: 0.78rem; font-family: var(--font-mono); line-height: 1.7;">
                    <tr><td style="color: var(--blue-700);">Platform:</td><td>Sentinel-1A (C-Band SAR)</td></tr>
                    <tr><td style="color: var(--blue-700);">Scene ID:</td><td>S1A_IW_GRDH_20261125</td></tr>
                    <tr><td style="color: var(--blue-700);">Observation Time:</td><td>25 Nov 05:42:11 UTC</td></tr>
                    <tr><td style="color: var(--blue-700);">Slick Area:</td><td><strong>14.82 km²</strong> (14,820,000 m²)</td></tr>
                    <tr><td style="color: var(--blue-700);">Perimeter:</td><td>32.40 km</td></tr>
                    <tr><td style="color: var(--blue-700);">Min σ⁰:</td><td>-24.8 dB</td></tr>
                  </table>
                </div>

                <div>
                  <h4 style="font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--blue-700); font-weight: 700; margin-bottom: 0.5rem;">
                    2. Culprit Vessel Identification
                  </h4>
                  <table style="width: 100%; font-size: 0.78rem; font-family: var(--font-mono); line-height: 1.7;">
                    <tr><td style="color: var(--blue-700);">Vessel Name:</td><td><strong>M/T Ocean Crown</strong></td></tr>
                    <tr><td style="color: var(--blue-700);">IMO / MMSI:</td><td>9481234 / 352981000</td></tr>
                    <tr><td style="color: var(--blue-700);">Flag State:</td><td>Panama (PA)</td></tr>
                    <tr><td style="color: var(--blue-700);">Vessel Class:</td><td>Crude Oil Tanker (158k DWT)</td></tr>
                    <tr><td style="color: var(--blue-700);">CPA Distance:</td><td><strong style="color: var(--coral-600);">0.38 nm (Direct Match)</strong></td></tr>
                    <tr><td style="color: var(--blue-700);">AIS Gap Period:</td><td>118 minutes (Unannounced)</td></tr>
                  </table>
                </div>
              </div>

              <!-- Cryptographic Verification Footer -->
              <div style="border-top: 1px solid var(--border-medium); padding-top: 1rem; margin-top: 1.25rem; font-family: var(--font-mono); font-size: 0.72rem; color: var(--blue-700);">
                <div style="display: flex; justify-content: space-between;">
                  <span>SHA-256 Provenance Hash:</span>
                  <span style="color: var(--blue-900);">e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-top: 0.35rem;">
                  <span>Audit Chain:</span>
                  <span>MARPOL Annex I · Law of the Sea Convention (UNCLOS Art. 211)</span>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button id="btn-modal-cancel" class="btn btn-outline btn-sm">Close</button>
            <button id="btn-modal-print" class="btn btn-primary btn-sm">
              <i data-lucide="printer" style="width: 14px; height: 14px;"></i>
              Print / Save as PDF
            </button>
          </div>
        </div>
      </div>
    `;
  },

  open() {
    const modal = document.getElementById('dossier-modal');
    if (modal) {
      modal.classList.add('open');
      lucide.createIcons();
    }
  },

  close() {
    const modal = document.getElementById('dossier-modal');
    if (modal) {
      modal.classList.remove('open');
    }
  },

  bindEvents() {
    const closeBtn = document.getElementById('btn-close-modal');
    const cancelBtn = document.getElementById('btn-modal-cancel');
    const printBtn = document.getElementById('btn-modal-print');
    const modal = document.getElementById('dossier-modal');

    if (closeBtn) closeBtn.addEventListener('click', () => this.close());
    if (cancelBtn) cancelBtn.addEventListener('click', () => this.close());
    if (modal) {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) this.close();
      });
    }

    if (printBtn) {
      printBtn.addEventListener('click', () => {
        window.print();
      });
    }
  }
};
