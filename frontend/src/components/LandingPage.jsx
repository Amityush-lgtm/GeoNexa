import React, { useEffect, useRef } from 'react';
import './LandingPage.css';

export default function LandingPage({ onEnter }) {
  const engineRef = useRef(null);

  useEffect(() => {
    // Always scroll to top when landing page mounts (reset orbital view)
    window.scrollTo({ top: 0, behavior: 'instant' });

    // Show loader while engine initialises
    const loadEl = document.getElementById('load');
    if (loadEl) {
      loadEl.style.display = 'grid';
      loadEl.style.opacity = '1';
      loadEl.style.pointerEvents = 'auto';
    }

    // Reset canvas opacity in case it was hidden during a previous ground stage
    const cv3d = document.getElementById('c');
    if (cv3d) cv3d.style.opacity = '1';

    // Reset realistic forest overlay
    const forestEl = document.getElementById('realisticForest');
    if (forestEl) forestEl.style.opacity = '0';

    // Reset haze overlay
    const hazeEl = document.getElementById('haze');
    if (hazeEl) hazeEl.style.opacity = '0';

    let engineInstance = null;

    const initEngine = () => {
      if (typeof window.initTerraEngine === 'function') {
        engineInstance = window.initTerraEngine({
          onEnter: (tab) => {
            if (onEnter) onEnter(tab || 'search');
          }
        });
        engineRef.current = engineInstance;
      }
    };

    // Script is loaded; re-init the scene each visit
    const existingScript = document.querySelector('script[data-terra-engine="true"]');
    if (existingScript && typeof window.initTerraEngine === 'function') {
      initEngine();
    } else if (!existingScript) {
      const script = document.createElement('script');
      script.src = '/terra-engine.js?v=' + Date.now();
      script.setAttribute('data-terra-engine', 'true');
      script.async = true;
      script.onload = initEngine;
      script.onerror = (e) => console.error('Failed to load terra-engine.js', e);
      document.body.appendChild(script);
    } else {
      // Script tag exists but not yet loaded
      existingScript.addEventListener('load', initEngine);
    }

    return () => {
      // Destroy engine on unmount (navigating away from landing)
      if (engineRef.current && typeof engineRef.current.destroy === 'function') {
        engineRef.current.destroy();
        engineRef.current = null;
      }
    };
  }, []); // Run once per mount — [] is intentional

  const handleNavClick = (tab) => {
    if (onEnter) onEnter(tab);
  };

  return (
    <div className="terra-page-container">
      {/* Loading overlay (hidden by engine on ready) */}
      <div id="load" className="terra-loader">
        <div className="terra-loader-box">
          <div className="terra-loader-rings">
            <div className="terra-ring ring-1"></div>
            <div className="terra-ring ring-2"></div>
            <div className="terra-ring ring-3"></div>
          </div>
          <div className="terra-loader-title">GEONEXA PLANETARY TELEMETRY</div>
          <div className="terra-loader-sub">SYNCHRONIZING ORBITAL SENSORS &amp; SHADERS…</div>
        </div>
      </div>

      {/* Scroll progress bar */}
      <div id="bar" className="terra-progress-bar"></div>

      {/* 800vh Scroller (drives Three.js scroll interpolation) */}
      <div id="scroller" className="terra-scroller"></div>

      {/* WebGL Canvas */}
      <canvas id="c" className="terra-canvas"></canvas>

      {/* Atmospheric Overlays */}
      <div className="vig"></div>
      <div id="haze"></div>
      <div id="flashx"></div>

      {/* Real-World Photorealistic Living Forest Layer (fades in at final descent) */}
      <div id="realisticForest" className="terra-realistic-forest">
        <img
          src="/realistic-forest.jpg"
          alt="Photorealistic Living Forest Canopy"
          className="terra-forest-img"
        />
        <div className="terra-forest-overlay"></div>
      </div>

      {/* Top Navbar */}
      <nav className="terra-nav">
        <div
          className="terra-brand-section"
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && window.scrollTo({ top: 0, behavior: 'smooth' })}
        >
          <span className="terra-brand-name">GEONEXA</span>
          <div className="terra-status-chip">
            <span className="terra-status-dot"></span>
            <span className="terra-status-text">AIR-GAPPED · SIH26227</span>
          </div>
        </div>

        <div className="terra-nav-items">
          <button type="button" onClick={() => handleNavClick('search')}>Semantic Search</button>
          <button type="button" onClick={() => handleNavClick('investigate')}>Tile Inspector</button>
          <button type="button" onClick={() => handleNavClick('change')}>Change Engine</button>
          <button type="button" onClick={() => handleNavClick('similar')}>Site Similarity</button>
          <button type="button" onClick={() => handleNavClick('provenance')}>Provenance</button>
          <button type="button" onClick={() => handleNavClick('archive')}>Archive Ops</button>
        </div>

        <button
          type="button"
          className="terra-launch-btn"
          onClick={() => handleNavClick('search')}
        >
          <span>Launch Platform</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12h14" />
            <path d="m12 5 7 7-7 7" />
          </svg>
        </button>
      </nav>

      {/* Text layers container (injected by engine with GeoNexa content) */}
      <div id="layers"></div>

      {/* Telemetry HUD */}
      <div id="hud">ALTITUDE 24,000 KM</div>

      {/* Scroll Down Hint */}
      <div id="hint">
        <span>SCROLL TO DESCEND</span>
        <i></i>
      </div>
    </div>
  );
}
