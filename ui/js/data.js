/**
 * OceanTrace Simulation & Detection Store
 * Fuses Sentinel-1 SAR observations with AIS trajectory datasets.
 */

const OceanTraceData = {
  activeIncidentId: 'OT-26143-A',

  sarScenes: [
    {
      id: 'S1A_IW_GRDH_1SDV_20261125T054211',
      name: 'Gulf of Oman (Major Shipping Corridor)',
      sensor: 'Sentinel-1A IW GRD',
      mode: 'Interferometric Wide Swath (IW)',
      resolution: '10 m / pixel',
      polarization: 'VV + VH',
      orbit: '142 (Descending)',
      acquisitionUtc: '2026-11-25 05:42:11 UTC',
      bounds: [[24.2, 56.4], [25.4, 58.1]],
      center: [24.812, 57.240]
    },
    {
      id: 'S1B_IW_GRDH_1SDV_20261124T181903',
      name: 'Strait of Malacca (Deepwater Channel)',
      sensor: 'Sentinel-1B IW GRD',
      mode: 'Interferometric Wide Swath (IW)',
      resolution: '10 m / pixel',
      polarization: 'VV + VH',
      orbit: '089 (Ascending)',
      acquisitionUtc: '2026-11-24 18:19:03 UTC',
      bounds: [[1.6, 101.4], [2.7, 103.0]],
      center: [2.148, 102.189]
    }
  ],

  incidents: {
    'OT-26143-A': {
      id: 'OT-26143-A',
      sceneId: 'S1A_IW_GRDH_1SDV_20261125T054211',
      locationName: 'Gulf of Oman — 42 nm Off Fujairah',
      centroid: [24.812, 57.240],
      detectionUtc: '2026-11-25 05:42:11 UTC',
      areaKm2: 14.82,
      areaM2: 14820000,
      perimeterKm: 32.40,
      circularity: 0.178,
      elongation: 3.82,
      minBackscatterDb: -24.8,
      meanSeaBackscatterDb: -11.2,
      contrastDb: 13.6,
      modelConfidence: 96.4,
      status: 'Correlated & Attributed',
      severity: 'CRITICAL DISCHARGE',
      culpritVesselMmsi: '352981000',
      culpritScore: 94.2
    },
    'OT-26143-B': {
      id: 'OT-26143-B',
      sceneId: 'S1A_IW_GRDH_1SDV_20261125T054211',
      locationName: 'North of Ras Al Hadd',
      centroid: [24.420, 57.810],
      detectionUtc: '2026-11-25 05:42:11 UTC',
      areaKm2: 3.41,
      areaM2: 3410000,
      perimeterKm: 14.20,
      circularity: 0.211,
      elongation: 2.15,
      minBackscatterDb: -21.4,
      meanSeaBackscatterDb: -10.9,
      contrastDb: 10.5,
      modelConfidence: 88.2,
      status: 'Under Drift Modeling',
      severity: 'MODERATE SLICK',
      culpritVesselMmsi: null,
      culpritScore: null
    }
  },

  driftSimulation: {
    incidentId: 'OT-26143-A',
    modelEngine: 'OpenDrift Lagrangian (Stokes Drift + Ekman)',
    particles: 5000,
    hindcastDurationHours: 14,
    estimatedDischargeUtc: '2026-11-24 16:30:00 UTC',
    metocean: {
      windVector: '8.4 m/s @ 315° (NW)',
      currentVector: '1.2 knots @ 132° (SE)',
      seaTemp: '28.4 °C',
      waveHeight: '1.1 m'
    },
    // Timesteps backwards from T-0 (05:42) to T-14h (15:42 previous day)
    timesteps: [
      { step: 0,  label: 'T-0h (Satellite Acquisition)', timeUtc: '25 Nov 05:42 UTC', lat: 24.812, lon: 57.240, areaKm2: 14.82, radius: 2400 },
      { step: -2, label: 'T-2h (Hindcast Drift)',        timeUtc: '25 Nov 03:42 UTC', lat: 24.782, lon: 57.210, areaKm2: 13.90, radius: 2150 },
      { step: -4, label: 'T-4h (Hindcast Drift)',        timeUtc: '25 Nov 01:42 UTC', lat: 24.750, lon: 57.175, areaKm2: 12.85, radius: 1900 },
      { step: -6, label: 'T-6h (Hindcast Drift)',        timeUtc: '24 Nov 23:42 UTC', lat: 24.715, lon: 57.135, areaKm2: 11.60, radius: 1650 },
      { step: -8, label: 'T-8h (Hindcast Drift)',        timeUtc: '24 Nov 21:42 UTC', lat: 24.678, lon: 57.090, areaKm2: 10.20, radius: 1400 },
      { step: -10,label: 'T-10h (Estimated Release Locus)', timeUtc: '24 Nov 19:42 UTC', lat: 24.640, lon: 57.045, areaKm2: 8.65, radius: 1100 },
      { step: -12,label: 'T-12h (Early Sheen Formation)', timeUtc: '24 Nov 17:42 UTC', lat: 24.605, lon: 57.000, areaKm2: 6.90, radius: 800 },
      { step: -14,label: 'T-14h (Initial Discharge Event)', timeUtc: '24 Nov 15:42 UTC', lat: 24.570, lon: 56.960, areaKm2: 4.80, radius: 500 }
    ]
  },

  candidateVessels: [
    {
      rank: 1,
      name: 'M/T Ocean Crown',
      mmsi: '352981000',
      imo: '9481234',
      callsign: '3FYE2',
      flag: 'Panama 🇵🇦',
      type: 'Crude Oil Tanker',
      dwt: '158,500 DWT',
      length: '274 m',
      beam: '48 m',
      cpaDistanceNm: '0.38 nm',
      cpaTimeUtc: '24 Nov 19:15 UTC',
      speedProfile: '14.2 kn → 5.1 kn (Anomaly) → 13.9 kn',
      aisStatus: 'Dark Window (118 min Gap)',
      aisGapDetails: 'Transponder switched off 24 Nov 18:40 to 20:38 UTC',
      correlationScore: 94.2,
      isCulprit: true,
      evidenceSummary: 'Direct spatio-temporal intersection with backwards drift origin cone. Unexplained 64% speed reduction and deliberate AIS transponder blackout during illegal bilge discharge window.'
    },
    {
      rank: 2,
      name: 'Pacific Voyager',
      mmsi: '563045000',
      imo: '9324567',
      callsign: '9V8921',
      flag: 'Singapore 🇸🇬',
      type: 'Container Ship',
      dwt: '68,200 DWT',
      length: '294 m',
      beam: '32 m',
      cpaDistanceNm: '4.82 nm',
      cpaTimeUtc: '24 Nov 20:45 UTC',
      speedProfile: 'Steady 19.4 kn',
      aisStatus: 'Continuous Broadcast',
      aisGapDetails: 'None (Regular 10s ping interval)',
      correlationScore: 24.1,
      isCulprit: false,
      evidenceSummary: 'Passed through traffic separation scheme at safe distance. Maintained consistent transit speed with uninterrupted AIS broadcasts.'
    },
    {
      rank: 3,
      name: 'Blue Marlin',
      mmsi: '636015000',
      imo: '9192837',
      callsign: 'A8LK3',
      flag: 'Liberia 🇱🇷',
      type: 'Bulk Carrier',
      dwt: '82,100 DWT',
      length: '229 m',
      beam: '32 m',
      cpaDistanceNm: '9.65 nm',
      cpaTimeUtc: '24 Nov 17:30 UTC',
      speedProfile: 'Steady 11.8 kn',
      aisStatus: 'Continuous Broadcast',
      aisGapDetails: 'None',
      correlationScore: 8.6,
      isCulprit: false,
      evidenceSummary: 'Outside primary Lagrangian dispersion envelope. Vector trajectory shows no correlation with spill formation.'
    },
    {
      rank: 4,
      name: 'Al-Sabah Star',
      mmsi: '403567000',
      imo: '9554321',
      callsign: 'HZZ8',
      flag: 'Saudi Arabia 🇸🇦',
      type: 'Chemical Tanker',
      dwt: '49,990 DWT',
      length: '183 m',
      beam: '32 m',
      cpaDistanceNm: '14.10 nm',
      cpaTimeUtc: '24 Nov 22:10 UTC',
      speedProfile: 'Steady 13.5 kn',
      aisStatus: 'Continuous Broadcast',
      aisGapDetails: 'None',
      correlationScore: 4.2,
      isCulprit: false,
      evidenceSummary: 'Distance to drift locus exceeds 14 nautical miles; negligible correlation.'
    }
  ]
};
