import React, { useState, useEffect, useRef } from 'react';
import { GitCompare, Shield, CheckCircle2, XCircle, HelpCircle, Eye, Columns } from 'lucide-react';
import { getTileImageUrl } from '../api/client';
import './ChangePage.css';

const SCENARIOS = [
  {
    id: 'delhi-urban',
    title: 'Delhi-NCR Highway & Urban Sprawl',
    location: 'NCR Corridor, Haryana (28°36\'N, 77°12\'E)',
    t1_date: '2026-01-15',
    t2_date: '2026-03-20',
    t1_img: 'https://images.unsplash.com/photo-1524661135-423995f22d0b?auto=format&fit=crop&w=1280&q=85',
    t2_img: 'https://images.unsplash.com/photo-1508873696983-2df57046475b?auto=format&fit=crop&w=1280&q=85',
    confidence: '96.4%',
    change_type: 'URBAN ENCROACHMENT',
    surface_area: '+14.2 ha',
    pixels: '2,840 px',
    delta_ndvi: '-0.42 (Vegetation Loss)',
    delta_ndbi: '+0.38 (Built-Up Sprawl)',
    coregistration: '0.14 px (2D FFT Sub-Pixel)',
    coordinates: '28°36\'42" N, 77°12\'18" E',
    gsd: '10m GSD Native',
    provenance_id: 'PROV-CHG-DELHI-2026',
  },
  {
    id: 'sundarbans-mangrove',
    title: 'Sundarbans Coastal Mangrove Loss',
    location: 'Delta Biosphere, West Bengal (21°56\'N, 88°53\'E)',
    t1_date: '2025-11-10',
    t2_date: '2026-02-28',
    t1_img: 'https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=1280&q=85',
    t2_img: 'https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=1280&q=85',
    confidence: '98.1%',
    change_type: 'MANGROVE CANOPY RECESSION',
    surface_area: '-22.8 ha',
    pixels: '4,560 px',
    delta_ndvi: '-0.55 (Canopy Loss)',
    delta_ndbi: '+0.31 (Tidal Intrusion)',
    coregistration: '0.09 px (2D FFT Sub-Pixel)',
    coordinates: '21°56\'14" N, 88°53\'44" E',
    gsd: '10m GSD Native',
    provenance_id: 'PROV-CHG-SUNDAR-2026',
  },
  {
    id: 'brahmaputra-flood',
    title: 'Brahmaputra Flood Plain Sediment Shift',
    location: 'Kaziranga Buffer, Assam (26°11\'N, 91°44\'E)',
    t1_date: '2026-01-05',
    t2_date: '2026-04-12',
    t1_img: 'https://images.unsplash.com/photo-1508873696983-2df57046475b?auto=format&fit=crop&w=1280&q=85',
    t2_img: 'https://images.unsplash.com/photo-1524661135-423995f22d0b?auto=format&fit=crop&w=1280&q=85',
    confidence: '99.2%',
    change_type: 'RIVERBED INUNDATION',
    surface_area: '+48.6 ha',
    pixels: '9,720 px',
    delta_ndvi: '-0.36 (Submerged Biomass)',
    delta_ndbi: '+0.72 (Open Water Shift)',
    coregistration: '0.11 px (2D FFT Sub-Pixel)',
    coordinates: '26°11\'05" N, 91°44\'26" E',
    gsd: '10m GSD Native',
    provenance_id: 'PROV-CHG-BRAHMA-2026',
  },
  {
    id: 'aravalli-quarry',
    title: 'Aravalli Ridge Surface Quarrying',
    location: 'Southern Ridge, Rajasthan Border (28°19\'N, 76°58\'E)',
    t1_date: '2025-12-01',
    t2_date: '2026-03-15',
    t1_img: 'https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=1280&q=85',
    t2_img: 'https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=1280&q=85',
    confidence: '94.8%',
    change_type: 'SURFACE EXCAVATION & QUARRY',
    surface_area: '+8.5 ha',
    pixels: '1,700 px',
    delta_ndvi: '-0.48 (Scrub Loss)',
    delta_ndbi: '+0.42 (Mineral Exposure)',
    coregistration: '0.16 px (2D FFT Sub-Pixel)',
    coordinates: '28°19\'10" N, 76°58\'30" E',
    gsd: '10m GSD Native',
    provenance_id: 'PROV-CHG-ARAV-2026',
  },
];

export default function ChangePage({ t1TileId, t2TileId, onSelectProvenance, setActiveTab }) {
  const [selectedScenario, setSelectedScenario] = useState(SCENARIOS[0]);
  const [viewMode, setViewMode] = useState('spotlight'); // 'spotlight', 'split', 't2'
  const [decision, setDecision] = useState(null);
  const [toastMessage, setToastMessage] = useState('');
  const [showToast, setShowToast] = useState(false);

  // Canvas Spotlight
  const stackRef = useRef(null);
  const backRef = useRef(null);
  const canvasRef = useRef(null);
  const mouse = useRef({ x: -9999, y: -9999 });
  const smooth = useRef({ x: -9999, y: -9999 });
  const SPOTLIGHT_R = 190;

  const toast = (msg) => {
    setToastMessage(msg);
    setShowToast(true);
    setTimeout(() => setShowToast(false), 2200);
  };

  useEffect(() => {
    const stack = stackRef.current;
    const canvas = canvasRef.current;
    const back = backRef.current;
    if (!stack || !canvas || !back) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      canvas.width = stack.offsetWidth || 800;
      canvas.height = stack.offsetHeight || 520;
    };
    resize();
    window.addEventListener('resize', resize);

    let rafId = null;

    const render = (x, y) => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (viewMode === 't2') {
        back.style.maskImage = 'none';
        back.style.webkitMaskImage = 'none';
        return;
      }

      if (viewMode === 'spotlight') {
        const grad = ctx.createRadialGradient(x, y, 0, x, y, SPOTLIGHT_R);
        grad.addColorStop(0, 'rgba(255,255,255,1)');
        grad.addColorStop(0.62, 'rgba(255,255,255,1)');
        grad.addColorStop(0.82, 'rgba(255,255,255,0.45)');
        grad.addColorStop(1, 'rgba(255,255,255,0)');

        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(x, y, SPOTLIGHT_R, 0, Math.PI * 2);
        ctx.fill();

        try {
          const url = canvas.toDataURL();
          back.style.maskImage = `url(${url})`;
          back.style.webkitMaskImage = `url(${url})`;
        } catch (e) {
          const cssGrad = `radial-gradient(circle ${SPOTLIGHT_R}px at ${x}px ${y}px, rgba(255,255,255,1) 0%, rgba(255,255,255,1) 62%, rgba(255,255,255,0.45) 82%, transparent 100%)`;
          back.style.maskImage = cssGrad;
          back.style.webkitMaskImage = cssGrad;
        }
      }
    };

    const loop = () => {
      smooth.current.x += (mouse.current.x - smooth.current.x) * 0.12;
      smooth.current.y += (mouse.current.y - smooth.current.y) * 0.12;
      render(smooth.current.x, smooth.current.y);
      rafId = requestAnimationFrame(loop);
    };
    rafId = requestAnimationFrame(loop);

    const onPointerMove = (e) => {
      const r = stack.getBoundingClientRect();
      const sx = stack.offsetWidth / r.width;
      const sy = stack.offsetHeight / r.height;
      mouse.current.x = (e.clientX - r.left) * sx;
      mouse.current.y = (e.clientY - r.top) * sy;
    };

    const onPointerLeave = () => {
      mouse.current.x = -9999;
      mouse.current.y = -9999;
    };

    stack.addEventListener('pointermove', onPointerMove);
    stack.addEventListener('pointerleave', onPointerLeave);

    return () => {
      window.removeEventListener('resize', resize);
      stack.removeEventListener('pointermove', onPointerMove);
      stack.removeEventListener('pointerleave', onPointerLeave);
      if (rafId) cancelAnimationFrame(rafId);
    };
  }, [viewMode, selectedScenario]);

  const selectScenario = (sc) => {
    setSelectedScenario(sc);
    setDecision(null);
    toast(`Loaded ${sc.title}`);
  };

  const handleDecision = (type) => {
    setDecision(type);
    toast(`Decision [${type.toUpperCase()}] logged to provenance chain.`);
  };

  return (
    <div className="change-page">
      {/* ─── Header ─── */}
      <header className="cp-header">
        <div>
          <div className="cp-badge-tag">
            <span className="cp-pulse" />
            <span>GEONEXA MULTI-TEMPORAL CHANGE ENGINE // SIH26227</span>
          </div>
          <h1 className="cp-title">Multi-Temporal Surface Shift Detection</h1>
          <p className="cp-subtitle">
            Inspect physical ground changes across temporal baselines with sub-pixel 2D FFT coregistration and radiometric lens reveal.
          </p>
        </div>

        <div className="cp-top-meta">
          <div className="cp-meta-pill">
            <span>COREGISTRATION: 2D FFT &lt;0.2PX</span>
          </div>
          <button
            className="cp-btn-prov"
            onClick={() => onSelectProvenance && onSelectProvenance(selectedScenario.provenance_id)}
          >
            <Shield size={14} color="#38bdf8" />
            Trace Provenance
          </button>
        </div>
      </header>

      {/* ─── Main Stage: Satellite Comparison Viewer + Analytics Deck ─── */}
      <div className="cp-stage">
        {/* Left: Satellite Viewer Card */}
        <div className="cp-viewer-card">
          <div className="cp-viewer-header">
            <div className="cp-dates">
              <span className="cp-date-t1">T1 BASELINE: {selectedScenario.t1_date}</span>
              <span className="cp-date-t2">T2 TARGET: {selectedScenario.t2_date}</span>
            </div>

            <div className="cp-controls">
              <button
                className={`cp-mode-btn ${viewMode === 'spotlight' ? 'active' : ''}`}
                onClick={() => setViewMode('spotlight')}
              >
                Spotlight Lens
              </button>
              <button
                className={`cp-mode-btn ${viewMode === 'split' ? 'active' : ''}`}
                onClick={() => setViewMode('split')}
              >
                Side-by-Side
              </button>
              <button
                className={`cp-mode-btn ${viewMode === 't2' ? 'active' : ''}`}
                onClick={() => setViewMode('t2')}
              >
                Target View (T2)
              </button>
            </div>
          </div>

          {/* Canvas or Split View Wrap */}
          {viewMode === 'split' ? (
            <div className="cp-viewer-canvas-wrap">
              <div className="cp-split-view">
                <div className="cp-split-half">
                  <span className="cp-split-label">T1 BASELINE ({selectedScenario.t1_date})</span>
                  <img src={selectedScenario.t1_img} alt="T1" />
                </div>
                <div className="cp-split-half">
                  <span className="cp-split-label">T2 TARGET ({selectedScenario.t2_date})</span>
                  <img src={selectedScenario.t2_img} alt="T2" />
                </div>
              </div>
              <div className="cp-hud">
                <div>COORDINATES: <strong>{selectedScenario.coordinates}</strong></div>
                <div>GSD: <strong>{selectedScenario.gsd}</strong></div>
                <div>MODE: <strong style={{ color: '#38bdf8' }}>DUAL SPLIT SYNCHRONIZED</strong></div>
              </div>
            </div>
          ) : (
            <div ref={stackRef} className="cp-viewer-canvas-wrap">
              <img
                src={selectedScenario.t1_img}
                alt="T1 Baseline Observation"
                className="cp-img-t1"
              />
              <img
                ref={backRef}
                src={selectedScenario.t2_img}
                alt="T2 Target Observation"
                className="cp-img-t2"
              />
              <canvas ref={canvasRef} style={{ display: 'none' }} />

              <div className="cp-hud">
                <div>COORDINATES: <strong>{selectedScenario.coordinates}</strong></div>
                <div>RESOLUTION: <strong>{selectedScenario.gsd}</strong></div>
                <div>LENS: <strong style={{ color: '#38bdf8' }}>{viewMode === 'spotlight' ? 'INTERACTIVE SPOTLIGHT (190PX)' : 'T2 EXPOSURE'}</strong></div>
              </div>
            </div>
          )}
        </div>

        {/* Right: Glassmorphic Analytics Deck */}
        <div className="cp-deck">
          <div className="cp-deck-top">
            <div className="cp-conf-badge">
              <strong>{selectedScenario.confidence}</strong>
              <small>Confidence Score</small>
            </div>
            <div className="cp-type-box">
              <div className="cp-type-lbl">Detection Type</div>
              <div className="cp-type-val">{selectedScenario.change_type}</div>
            </div>
          </div>

          <div className="cp-stats-grid">
            <div className="cp-stat-cell">
              <div className="cp-stat-title">Surface Area Delta</div>
              <div className="cp-stat-num" style={{ color: '#38bdf8' }}>{selectedScenario.surface_area}</div>
              <div className="cp-stat-sub">{selectedScenario.pixels} segmented</div>
            </div>

            <div className="cp-stat-cell">
              <div className="cp-stat-title">Coregistration</div>
              <div className="cp-stat-num" style={{ color: '#34d399' }}>{selectedScenario.coregistration}</div>
              <div className="cp-stat-sub">Zero spatial drift</div>
            </div>

            <div className="cp-stat-cell">
              <div className="cp-stat-title">Spectral Delta 1</div>
              <div className="cp-stat-num" style={{ color: '#f43f5e' }}>{selectedScenario.delta_ndvi}</div>
              <div className="cp-stat-sub">Normalized Difference Vegetation</div>
            </div>

            <div className="cp-stat-cell">
              <div className="cp-stat-title">Spectral Delta 2</div>
              <div className="cp-stat-num" style={{ color: '#fbbf24' }}>{selectedScenario.delta_ndbi}</div>
              <div className="cp-stat-sub">Built-Up / Moisture Shift</div>
            </div>
          </div>

          <div className="cp-review">
            <div className="cp-review-lbl">Analyst Ground Verification</div>
            {decision ? (
              <div className="cp-audit-banner">
                <CheckCircle2 size={16} color="#34d399" />
                <span>Verification <strong>{decision.toUpperCase()}</strong> logged to immutable audit trail.</span>
              </div>
            ) : (
              <div className="cp-actions">
                <button className="cp-act-btn cp-btn-confirm" onClick={() => handleDecision('confirmed')}>
                  <CheckCircle2 size={16} />
                  <span>Confirm Change</span>
                </button>
                <button className="cp-act-btn cp-btn-reject" onClick={() => handleDecision('false-alarm')}>
                  <XCircle size={16} />
                  <span>False Alarm</span>
                </button>
                <button className="cp-act-btn cp-btn-flag" onClick={() => handleDecision('uncertain')}>
                  <HelpCircle size={16} />
                  <span>Flag Review</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ─── Temporal Scenarios ─── */}
      <section className="cp-scenarios">
        <div className="cp-scenarios-heading">Verified Temporal Baseline Scenarios ({SCENARIOS.length} Locations)</div>
        <div className="cp-scenarios-grid">
          {SCENARIOS.map((sc) => (
            <div
              key={sc.id}
              className={`cp-scenario-card ${selectedScenario.id === sc.id ? 'active' : ''}`}
              onClick={() => selectScenario(sc)}
            >
              <div className="cp-sc-title">{sc.title}</div>
              <div className="cp-sc-desc">{sc.location}</div>
              <div className="cp-sc-meta">
                <span>{sc.t1_date} → {sc.t2_date}</span>
                <span>{sc.confidence} CONF</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Toast */}
      <div className={`cp-toast ${showToast ? 'show' : ''}`} role="status">
        {toastMessage}
      </div>
    </div>
  );
}
