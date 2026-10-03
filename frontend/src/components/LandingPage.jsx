import React, { useEffect, useRef, useState } from 'react';
import './LandingPage.css';

export default function LandingPage({ onEnter }) {
  const [engineReady, setEngineReady] = useState(false);
  const engineRef = useRef(null);

  useEffect(() => {
    let scriptLoaded = false;
    let engineInstance = null;

    // Check if script is already present
    let script = document.querySelector('script[src="/terra-engine.js"]');
    
    const initEngine = () => {
      if (typeof window.initTerraEngine === 'function') {
        engineInstance = window.initTerraEngine({
          onEnter: (tab) => {
            if (onEnter) onEnter(tab || 'search');
          }
        });
        engineRef.current = engineInstance;
        setEngineReady(true);
      }
    };

    if (!script) {
      script = document.createElement('script');
      script.src = '/terra-engine.js';
      script.async = true;
      script.onload = () => {
        scriptLoaded = true;
        initEngine();
      };
      script.onerror = (e) => {
        console.error('Failed to load terra-engine.js', e);
      };
      document.body.appendChild(script);
    } else {
      if (typeof window.initTerraEngine === 'function') {
        initEngine();
      } else {
        script.addEventListener('load', initEngine);
      }
    }

    return () => {
      if (engineRef.current && typeof engineRef.current.destroy === 'function') {
        engineRef.current.destroy();
        engineRef.current = null;
      }
    };
  }, [onEnter]);

  const handleNavClick = (tab) => {
    if (onEnter) onEnter(tab);
  };

  return (
    <div className="terra-page-container">
      {/* Loading overlay (removed by engine once compiled) */}
      <div id="load" className="terra-loader">
        <div className="terra-loader-box">
          <div className="terra-loader-rings">
            <div className="terra-ring ring-1"></div>
            <div className="terra-ring ring-2"></div>
            <div className="terra-ring ring-3"></div>
          </div>
          <div className="terra-loader-title">GEONEXA PLANETARY TELEMETRY</div>
          <div className="terra-loader-sub">SYNCHRONIZING ORBITAL SENSORS & SHADERS…</div>
        </div>
      </div>

      {/* Scroll progress bar */}
      <div id="bar" className="terra-progress-bar"></div>

      {/* 800vh Scroller */}
      <div id="scroller" className="terra-scroller"></div>

      {/* WebGL Canvas */}
      <canvas id="c" className="terra-canvas"></canvas>

      {/* Atmospheric Overlays */}
      <div className="vig"></div>
      <div id="haze"></div>
      <div id="flashx"></div>

      {/* Real-World Photorealistic Living Forest Layer (Fades in at ground descent) */}
      <div id="realisticForest" className="terra-realistic-forest">
        <img
          src="/realistic-forest.jpg"
          alt="Photorealistic Living Forest Canopy"
          className="terra-forest-img"
        />
        <video
          src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260613_180732_a54afbf6-b30d-470e-861f-669871f09f67.mp4"
          autoPlay
          loop
          muted
          playsInline
          className="terra-forest-video"
        ></video>
        <div className="terra-forest-overlay"></div>
      </div>

      {/* Top Navbar */}
      <nav className="terra-nav">
        <div
          className="terra-brand-section"
          onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          role="button"
          tabIndex={0}
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
