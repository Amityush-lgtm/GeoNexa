import React, { useState, useEffect, useRef } from 'react';
import './LandingPage.css';

const NAV_LINKS = [
  { label: 'Semantic Search', tab: 'search' },
  { label: 'Tile Inspector', tab: 'investigate' },
  { label: 'Change Engine', tab: 'change' },
  { label: 'Provenance Trace', tab: 'provenance' },
];

const MOBILE_NAV_LINKS = [
  { label: 'Semantic Search', tab: 'search' },
  { label: 'Tile Inspector', tab: 'investigate' },
  { label: 'Change Engine', tab: 'change' },
  { label: 'Site Similarity', tab: 'similar' },
  { label: 'Provenance Trace', tab: 'provenance' },
  { label: 'Archive Operations', tab: 'archive' },
];

const RAINBOW_SRC =
  'https://soft-zoom-63098134.figma.site/_assets/v11/8d520a7515d06cbfc403d0125e3d05b1a7ccd29c.png';
const CLOUD_SRC =
  'https://soft-zoom-63098134.figma.site/_assets/v11/0d6dfd3f90b930f21726f2ed56a3320d79b7a797.png';

function clamp(min, max, v) {
  return Math.min(max, Math.max(min, v));
}

function lerp(current, target, factor) {
  return current + (target - current) * factor;
}

export default function LandingPage({ onEnter }) {
  const [menuOpen, setMenuOpen] = useState(false);

  // QuoteSection parallax refs
  const quoteSectionRef = useRef(null);
  const rainbowRef = useRef(null);
  const leftCloudRef = useRef(null);
  const rightCloudRef = useRef(null);

  // Lock body scroll when mobile menu is open
  useEffect(() => {
    if (menuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [menuOpen]);

  // QuoteSection parallax animation
  useEffect(() => {
    let rafId;

    const current = {
      rainbowY: 120,
      leftCloudX: -200,
      leftCloudY: 0,
      rightCloudX: 200,
      rightCloudY: 0,
    };

    function animate() {
      const section = quoteSectionRef.current;
      if (!section) {
        rafId = requestAnimationFrame(animate);
        return;
      }

      const rect = section.getBoundingClientRect();
      const wh = window.innerHeight;
      const progress = clamp(0, 1, (wh - rect.top) / (wh + rect.height));

      // Rainbow: moves from +120px to -160px
      const rainbowTargetY = 120 + progress * (-160 - 120);
      current.rainbowY = lerp(current.rainbowY, rainbowTargetY, 0.06);

      if (rainbowRef.current) {
        rainbowRef.current.style.transform = `translate3d(0, ${current.rainbowY}px, 0)`;
      }

      // Clouds: slide in when progress is between 0.12 and 0.92
      const cloudVisible = progress > 0.12 && progress < 0.92;
      const leftTargetX = cloudVisible ? 0 : -200;
      const rightTargetX = cloudVisible ? 0 : 200;
      const cloudTargetY = progress * -50;

      current.leftCloudX = lerp(current.leftCloudX, leftTargetX, 0.04);
      current.leftCloudY = lerp(current.leftCloudY, cloudTargetY, 0.04);
      current.rightCloudX = lerp(current.rightCloudX, rightTargetX, 0.04);
      current.rightCloudY = lerp(current.rightCloudY, cloudTargetY, 0.04);

      // Opacity tied to distance from target
      const leftOpacity = clamp(0, 1, 1 - Math.abs(current.leftCloudX) / 200);
      const rightOpacity = clamp(0, 1, 1 - Math.abs(current.rightCloudX) / 200);

      if (leftCloudRef.current) {
        leftCloudRef.current.style.transform = `translate3d(${current.leftCloudX}px, ${current.leftCloudY}px, 0)`;
        leftCloudRef.current.style.opacity = String(leftOpacity);
      }

      if (rightCloudRef.current) {
        rightCloudRef.current.style.transform = `translate3d(${current.rightCloudX}px, ${current.rightCloudY}px, 0) scaleX(-1)`;
        rightCloudRef.current.style.opacity = String(rightOpacity);
      }

      rafId = requestAnimationFrame(animate);
    }

    rafId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafId);
  }, []);

  const handleNavClick = (tab) => {
    if (onEnter) onEnter(tab);
  };

  return (
    <div className="serene-landing-wrapper">
      {/* ─── SECTION 1: HERO ─── */}
      <section className="serene-hero">
        {/* Background video */}
        <video
          autoPlay
          muted
          loop
          playsInline
          className="serene-video"
        >
          <source
            src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260613_180732_a54afbf6-b30d-470e-861f-669871f09f67.mp4"
            type="video/mp4"
          />
        </video>

        {/* Dark overlay */}
        <div className="serene-overlay" />

        {/* ─── Navbar ─── */}
        <nav className="serene-nav">
          {/* Brand */}
          <a
            href="#"
            className="serene-brand"
            onClick={(e) => {
              e.preventDefault();
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
          >
            GeoNexa
          </a>

          {/* Desktop links */}
          <div className="serene-desktop-links">
            {NAV_LINKS.map(({ label, tab }) => (
              <a
                key={label}
                href="#"
                className="serene-nav-link"
                onClick={(e) => {
                  e.preventDefault();
                  handleNavClick(tab);
                }}
              >
                {label}
              </a>
            ))}
          </div>

          {/* Desktop CTA */}
          <button
            onClick={() => handleNavClick('search')}
            className="serene-nav-cta"
          >
            Launch Platform
          </button>

          {/* Mobile hamburger */}
          <button
            className="serene-hamburger"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label="Toggle menu"
          >
            <span
              className="serene-hamburger-bar"
              style={{
                transform: menuOpen
                  ? 'rotate(45deg) translateY(9px)'
                  : 'rotate(0) translateY(0)',
              }}
            />
            <span
              className="serene-hamburger-bar"
              style={{
                opacity: menuOpen ? 0 : 1,
                transform: menuOpen ? 'scaleX(0)' : 'scaleX(1)',
              }}
            />
            <span
              className="serene-hamburger-bar"
              style={{
                transform: menuOpen
                  ? 'rotate(-45deg) translateY(-9px)'
                  : 'rotate(0) translateY(0)',
              }}
            />
          </button>

          {/* Mobile menu overlay */}
          <div
            className="serene-mobile-overlay"
            style={{
              opacity: menuOpen ? 1 : 0,
              pointerEvents: menuOpen ? 'auto' : 'none',
            }}
            onClick={() => setMenuOpen(false)}
          />

          {/* Mobile slide-in panel */}
          <div
            className="serene-mobile-panel"
            style={{
              transform: menuOpen ? 'translateX(0)' : 'translateX(100%)',
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
              {MOBILE_NAV_LINKS.map(({ label, tab }, i) => (
                <a
                  key={label}
                  href="#"
                  className="serene-mobile-link"
                  style={{
                    fontSize: '1.25rem',
                    transitionDelay: menuOpen ? `${150 + i * 60}ms` : '0ms',
                    opacity: menuOpen ? 1 : 0,
                    transform: menuOpen ? 'translateX(0)' : 'translateX(30px)',
                  }}
                  onClick={(e) => {
                    e.preventDefault();
                    setMenuOpen(false);
                    handleNavClick(tab);
                  }}
                >
                  {label}
                </a>
              ))}
            </div>

            <button
              onClick={() => {
                setMenuOpen(false);
                handleNavClick('search');
              }}
              className="serene-mobile-cta"
              style={{
                transitionDelay: menuOpen ? '500ms' : '0ms',
                opacity: menuOpen ? 1 : 0,
                transform: menuOpen ? 'translateX(0)' : 'translateX(30px)',
              }}
            >
              Launch Platform
            </button>
          </div>
        </nav>

        {/* ─── Center content ─── */}
        <div className="serene-hero-center">
          <h1 className="serene-hero-heading">
            See Earth.
            <br />
            Query everything.
          </h1>

          <p className="serene-hero-subtext">
            Air-gapped semantic satellite search powered by fine-tuned RemoteCLIP.
            Natural-language retrieval, multi-temporal change detection, and cryptographic provenance.
          </p>

          <button
            onClick={() => handleNavClick('search')}
            className="serene-hero-cta"
          >
            Launch Search Platform
          </button>
        </div>

        {/* ─── Status indicator (desktop only) ─── */}
        <div className="serene-sound-indicator">
          <div className="serene-sound-circle">
            <div
              className="pulse-indicator"
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: '#38bdf8',
                boxShadow: '0 0 10px #38bdf8',
              }}
            />
          </div>
          <div className="serene-sound-text-col">
            <span className="serene-sound-text" style={{ fontWeight: 600, color: '#f0f4ff' }}>
              Offline active
            </span>
            <span className="serene-sound-text">
              Air-gapped · SIH26227
            </span>
          </div>
        </div>
      </section>

      {/* ─── SECTION 2: MISSION QUOTE SECTION ─── */}
      <section
        ref={quoteSectionRef}
        className="serene-quote-section"
      >
        {/* Rainbow image */}
        <img
          ref={rainbowRef}
          src={RAINBOW_SRC}
          alt=""
          className="serene-rainbow"
        />

        {/* Left cloud */}
        <img
          ref={leftCloudRef}
          src={CLOUD_SRC}
          alt=""
          className="serene-left-cloud"
        />

        {/* Right cloud (flipped) */}
        <img
          ref={rightCloudRef}
          src={CLOUD_SRC}
          alt=""
          className="serene-right-cloud"
        />

        {/* Quote content */}
        <div className="serene-quote-container">
          <div className="serene-quote-inner">
            <p className="serene-quote-text">
              &ldquo;GeoNexa was founded on the conviction that national Earth observation
              intelligence should require zero cloud reliance to deliver truth. We pursue
              deterministic outcomes from raw satellite archives — physics-grounded spectral
              indices, sub-pixel coregistration, and cryptographic provenance. We understand
              the physical terrain before deciding what has changed. No cloud, no telemetry&nbsp;&mdash;
              just pure geospatial signal.&rdquo;
            </p>

            <p className="serene-quote-author">
              GeoNexa Intelligence Platform&nbsp;&mdash; Smart India Hackathon 2026 (SIH26227)
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
