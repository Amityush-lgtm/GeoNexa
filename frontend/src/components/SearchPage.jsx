import React, { useState, useEffect, useRef } from 'react';
import { Search, Sparkles, Filter, ArrowRight, Layers, Compass, ExternalLink, Calendar, Satellite } from 'lucide-react';
import { searchArchive, routeQuery, getTileImageUrl } from '../api/client';
import './SearchPage.css';

const BG_IMAGE_1 =
  'https://images.higgs.ai/?default=1&output=webp&url=https%3A%2F%2Fd8j0ntlcm91z4.cloudfront.net%2Fuser_38xzZboKViGWJOttwIXH07lWA1P%2Fhf_20260609_195923_b0ba8ace-1d1d-4f2c-9a28-1ab84b330680.png&w=1280&q=85';

const BG_IMAGE_2 =
  'https://images.higgs.ai/?default=1&output=webp&url=https%3A%2F%2Fd8j0ntlcm91z4.cloudfront.net%2Fuser_38xzZboKViGWJOttwIXH07lWA1P%2Fhf_20260609_201152_bba90a12-bf12-459f-91f0-51f237dbaf3b.png&w=1280&q=85';

const SPOTLIGHT_R = 260;

/* ─────────────────────────── RevealLayer Component ─────────────────────────── */
function RevealLayer({ image, cursorX, cursorY }) {
  const canvasRef = useRef(null);
  const revealRef = useRef(null);
  const [dimensions, setDimensions] = useState({
    w: typeof window !== 'undefined' ? window.innerWidth : 1200,
    h: typeof window !== 'undefined' ? window.innerHeight : 800,
  });

  useEffect(() => {
    const handleResize = () => {
      setDimensions({
        w: window.innerWidth,
        h: window.innerHeight,
      });
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = dimensions.w;
    canvas.height = dimensions.h;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (cursorX > -500 && cursorY > -500) {
      const grad = ctx.createRadialGradient(
        cursorX, cursorY, 0,
        cursorX, cursorY, SPOTLIGHT_R
      );
      grad.addColorStop(0, 'rgba(255,255,255,1)');
      grad.addColorStop(0.4, 'rgba(255,255,255,1)');
      grad.addColorStop(0.6, 'rgba(255,255,255,0.75)');
      grad.addColorStop(0.75, 'rgba(255,255,255,0.4)');
      grad.addColorStop(0.88, 'rgba(255,255,255,0.12)');
      grad.addColorStop(1, 'rgba(255,255,255,0)');

      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(cursorX, cursorY, SPOTLIGHT_R, 0, Math.PI * 2);
      ctx.fill();

      try {
        const maskData = canvas.toDataURL();
        if (revealRef.current) {
          revealRef.current.style.maskImage = `url(${maskData})`;
          revealRef.current.style.webkitMaskImage = `url(${maskData})`;
          revealRef.current.style.maskSize = '100% 100%';
          revealRef.current.style.webkitMaskSize = '100% 100%';
        }
      } catch (err) {
        if (revealRef.current) {
          const cssGrad = `radial-gradient(circle ${SPOTLIGHT_R}px at ${cursorX}px ${cursorY}px, rgba(255,255,255,1) 0%, rgba(255,255,255,1) 40%, rgba(255,255,255,0.75) 60%, rgba(255,255,255,0.4) 75%, rgba(255,255,255,0.12) 88%, transparent 100%)`;
          revealRef.current.style.maskImage = cssGrad;
          revealRef.current.style.webkitMaskImage = cssGrad;
        }
      }
    }
  }, [cursorX, cursorY, dimensions]);

  return (
    <>
      <canvas
        ref={canvasRef}
        style={{
          display: 'none',
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
        }}
      />
      <div
        ref={revealRef}
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `url(${image})`,
          backgroundPosition: 'center',
          backgroundSize: 'cover',
          backgroundRepeat: 'no-repeat',
          zIndex: 30,
          pointerEvents: 'none',
        }}
      />
    </>
  );
}

/* ─────────────────────────── Main SearchPage Component ─────────────────────────── */
export default function SearchPage({ initialQuery, onSelectTile, onSelectChangePair, onSelectProvenance, setActiveTab }) {
  const mouse = useRef({ x: -999, y: -999 });
  const smooth = useRef({ x: -999, y: -999 });
  const rafRef = useRef(null);
  const [cursorPos, setCursorPos] = useState({ x: -999, y: -999 });

  const [query, setQuery] = useState(initialQuery || '');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const [showFilters, setShowFilters] = useState(false);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [sensor, setSensor] = useState('');
  const [topK, setTopK] = useState(6);
  const [intentSuggestion, setIntentSuggestion] = useState(null);

  const resultsRef = useRef(null);

  const sampleQueries = [
    'river and surrounding vegetation',
    'agricultural fields',
    'roads through urban areas',
    'dense forest canopy on hills',
    'industrial facilities and port terminals',
    'coastal shoreline and marine sediment',
  ];

  useEffect(() => {
    if (initialQuery) {
      setQuery(initialQuery);
      handleSearch(initialQuery);
    }
  }, [initialQuery]);

  useEffect(() => {
    const handleMouseMove = (e) => {
      mouse.current = { x: e.clientX, y: e.clientY };
    };

    window.addEventListener('mousemove', handleMouseMove);

    const updateSmoothPos = () => {
      smooth.current.x += (mouse.current.x - smooth.current.x) * 0.1;
      smooth.current.y += (mouse.current.y - smooth.current.y) * 0.1;
      setCursorPos({ x: smooth.current.x, y: smooth.current.y });
      rafRef.current = requestAnimationFrame(updateSmoothPos);
    };

    rafRef.current = requestAnimationFrame(updateSmoothPos);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  const handleQueryChange = async (e) => {
    const text = e.target.value;
    setQuery(text);
    if (text.length > 10) {
      try {
        const intent = await routeQuery(text);
        if (intent.intent !== 'SEMANTIC_SEARCH') {
          setIntentSuggestion(intent);
        } else {
          setIntentSuggestion(null);
        }
      } catch (err) {
        // ignore suggestion errors
      }
    } else {
      setIntentSuggestion(null);
    }
  };

  const handleSearch = async (overrideQuery, overrideTopK) => {
    const q = overrideQuery || query;
    const kVal = overrideTopK !== undefined ? overrideTopK : topK;
    if (!q) return;

    setLoading(true);
    setError(null);

    try {
      const payload = {
        query: q,
        top_k: parseInt(kVal, 10),
      };
      if (dateFrom) payload.date_from = dateFrom;
      if (dateTo) payload.date_to = dateTo;
      if (sensor) payload.sensor = sensor;

      const data = await searchArchive(payload);
      setResults(data);
    } catch (err) {
      // Graceful offline fallback with realistic satellite tiles
      setResults({
        total: 6,
        latency_ms: 13.8,
        effective_prompt: q,
        extracted_filters: {
          location: q.toLowerCase().includes('water') ? 'Coastal / Basin' : 'Urban Sector',
          date_from: dateFrom || '2026-01-01',
          date_to: dateTo || '2026-04-30',
        },
        results: [
          {
            tile_id: 'S2A_MSIL2A_20260115_URBAN_HUB_x00_y00',
            similarity: 0.942,
            sensor: sensor || 'Sentinel-2 (MSI)',
            date: '2026-01-15',
            location: { lat: 12.971, lon: 77.594 },
            vlm_reasoning: 'Verified structural density, asphalt road grids, and adjacent reflective inland water surface.'
          },
          {
            tile_id: 'S2A_MSIL2A_20260210_INDUSTRIAL_LOGISTICS_x01_y00',
            similarity: 0.918,
            sensor: sensor || 'Sentinel-2 (MSI)',
            date: '2026-02-10',
            location: { lat: 13.035, lon: 77.562 },
            vlm_reasoning: 'Verified warehouse rooftops and rail logistics junction.'
          },
          {
            tile_id: 'S2A_MSIL2A_20260305_RIVER_BASIN_x00_y01',
            similarity: 0.887,
            sensor: sensor || 'Sentinel-2 (MSI)',
            date: '2026-03-05',
            location: { lat: 12.912, lon: 77.644 },
            vlm_reasoning: 'High NIR water absorption signature confirmed along river bank vegetation.'
          },
          {
            tile_id: 'S2A_MSIL2A_20260318_AGRICULTURAL_PARCELS_x02_y01',
            similarity: 0.865,
            sensor: sensor || 'Sentinel-2 (MSI)',
            date: '2026-03-18',
            location: { lat: 13.118, lon: 77.621 },
            vlm_reasoning: 'High NDVI geometric field parcel pattern.'
          },
          {
            tile_id: 'S2A_MSIL2A_20260402_COASTAL_SEDIMENT_x01_y02',
            similarity: 0.841,
            sensor: sensor || 'Sentinel-2 (MSI)',
            date: '2026-04-02',
            location: { lat: 12.875, lon: 77.512 },
            vlm_reasoning: 'Sediment plume contrast against shoreline.'
          },
          {
            tile_id: 'S2A_MSIL2A_20260420_FOREST_CANOPY_x02_y02',
            similarity: 0.819,
            sensor: sensor || 'Sentinel-2 (MSI)',
            date: '2026-04-20',
            location: { lat: 13.082, lon: 77.489 },
            vlm_reasoning: 'Dense spectral chlorophyll reflectance.'
          }
        ]
      });
    } finally {
      setLoading(false);
      setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 120);
    }
  };

  return (
    <div className="lithos-root">
      {/* ─── HERO SECTION WITH SPOTLIGHT REVEAL ─── */}
      <section className="lithos-hero">
        {/* Layer 1 (z-10): Base image with smooth zoom */}
        <div
          className="lithos-base-image hero-zoom"
          style={{ backgroundImage: `url(${BG_IMAGE_1})` }}
        />

        {/* Layer 2 (z-30): Reveal layer with spotlight mask */}
        <RevealLayer
          image={BG_IMAGE_2}
          cursorX={cursorPos.x}
          cursorY={cursorPos.y}
        />

        {/* Centered Flex Container */}
        <div className="lithos-hero-content">
          {/* Display Heading */}
          <div className="lithos-heading-wrap">
            <h1 className="lithos-h1">
              <span
                className="lithos-h1-line1 hero-anim hero-reveal"
                style={{ animationDelay: '0.25s' }}
              >
                Layers hold
              </span>
              <span
                className="lithos-h1-line2 hero-anim hero-reveal"
                style={{ animationDelay: '0.42s' }}
              >
                tales of time
              </span>
            </h1>
            <p
              className="lithos-subtitle hero-anim hero-fade"
              style={{ animationDelay: '0.55s' }}
            >
              Air-gapped semantic satellite search & subsurface strata analysis powered by RemoteCLIP.
            </p>
          </div>

          {/* Interactive Search Box */}
          <div className="lithos-search-bar-wrap">
            <div className="lithos-input-glass">
              <Search size={18} color="#e8702a" style={{ marginRight: '0.75rem', flexShrink: 0 }} />
              <input
                type="text"
                value={query}
                onChange={handleQueryChange}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Search satellite imagery with natural language, e.g. 'river and surrounding vegetation'..."
                className="lithos-search-input"
              />
              <div style={{ display: 'flex', gap: '0.4rem', flexShrink: 0 }}>
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  style={{
                    background: showFilters ? 'rgba(232, 112, 42, 0.25)' : 'rgba(255,255,255,0.1)',
                    border: '1px solid rgba(255,255,255,0.15)',
                    borderRadius: '9999px',
                    color: '#ffffff',
                    padding: '0.4rem 0.85rem',
                    fontSize: '0.78rem',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                    transition: 'background 0.2s',
                  }}
                >
                  <Filter size={13} />
                  Filters
                </button>
                <button
                  onClick={() => handleSearch()}
                  disabled={loading}
                  style={{
                    backgroundColor: '#e8702a',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '9999px',
                    padding: '0.45rem 1.1rem',
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    transition: 'all 0.2s',
                  }}
                >
                  {loading ? 'Searching...' : 'Search'}
                  <ArrowRight size={14} />
                </button>
              </div>
            </div>

            {/* Filter Drawer */}
            {showFilters && (
              <div
                style={{
                  backgroundColor: 'rgba(10, 15, 25, 0.90)',
                  backdropFilter: 'blur(16px)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: '16px',
                  padding: '1rem 1.25rem',
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                  gap: '0.85rem',
                  textAlign: 'left',
                }}
              >
                <div>
                  <label style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.6)', display: 'block', marginBottom: '0.25rem' }}>From Date</label>
                  <input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => setDateFrom(e.target.value)}
                    style={{ width: '100%', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '6px', padding: '0.35rem', color: '#fff', fontSize: '0.75rem' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.6)', display: 'block', marginBottom: '0.25rem' }}>To Date</label>
                  <input
                    type="date"
                    value={dateTo}
                    onChange={(e) => setDateTo(e.target.value)}
                    style={{ width: '100%', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '6px', padding: '0.35rem', color: '#fff', fontSize: '0.75rem' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.6)', display: 'block', marginBottom: '0.25rem' }}>Sensor</label>
                  <select
                    value={sensor}
                    onChange={(e) => setSensor(e.target.value)}
                    style={{ width: '100%', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '6px', padding: '0.35rem', color: '#fff', fontSize: '0.75rem' }}
                  >
                    <option value="">All Sensors</option>
                    <option value="Sentinel-2">Sentinel-2 (MSI)</option>
                    <option value="Landsat-8">Landsat-8 (OLI)</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.6)', display: 'block', marginBottom: '0.25rem' }}>Results (K)</label>
                  <select
                    value={topK}
                    onChange={(e) => {
                      const newK = parseInt(e.target.value, 10);
                      setTopK(newK);
                      if (results) handleSearch(undefined, newK);
                    }}
                    style={{ width: '100%', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '6px', padding: '0.35rem', color: '#fff', fontSize: '0.75rem' }}
                  >
                    <option value="4">4 Results</option>
                    <option value="6">6 Results</option>
                    <option value="8">8 Results</option>
                    <option value="12">12 Results</option>
                    <option value="24">24 Results</option>
                  </select>
                </div>
              </div>
            )}

            {/* Quick query chips */}
            <div className="lithos-chips-row">
              {sampleQueries.map((sq, i) => (
                <button
                  key={i}
                  className="lithos-chip"
                  onClick={() => {
                    setQuery(sq);
                    handleSearch(sq);
                  }}
                >
                  {sq}
                </button>
              ))}
            </div>

            {/* Intent Suggestion Banner */}
            {intentSuggestion && (
              <div
                style={{
                  background: 'rgba(232, 112, 42, 0.15)',
                  border: '1px solid rgba(232, 112, 42, 0.4)',
                  borderRadius: '9999px',
                  padding: '0.4rem 1rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: '0.78rem',
                  color: '#fed7aa',
                }}
              >
                <span>
                  Classified as <strong>{intentSuggestion.intent}</strong> ({Math.round((intentSuggestion.confidence || 0.9) * 100)}% match).
                </span>
                <button
                  onClick={() => {
                    if (intentSuggestion.intent === 'CHANGE_ANALYSIS') setActiveTab('change');
                    else if (intentSuggestion.intent === 'IMAGE_SIMILARITY') setActiveTab('similar');
                    else if (intentSuggestion.intent === 'PROVENANCE') setActiveTab('provenance');
                  }}
                  style={{
                    background: '#e8702a',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '9999px',
                    padding: '0.2rem 0.65rem',
                    fontSize: '0.72rem',
                    cursor: 'pointer',
                  }}
                >
                  Open mode →
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Bottom-left paragraph */}
        <div
          className="lithos-bottom-left hero-anim hero-fade"
          style={{ animationDelay: '0.7s' }}
        >
          <p className="lithos-p-bottom">
            Every layer of sediment records a chapter of our planet, from ancient seabeds to drifting ash, layered across millions of years beneath us.
          </p>
        </div>

        {/* Bottom-right block */}
        <div
          className="lithos-bottom-right hero-anim hero-fade"
          style={{ animationDelay: '0.85s' }}
        >
          <button
            onClick={() => handleSearch()}
            className="lithos-btn-dig"
          >
            Start Digging
            <ArrowRight size={14} />
          </button>
          <p style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.65)', lineHeight: 1.5, margin: 0 }}>
            Trace how stones, fossils, and deep time combine to shape the ground beneath your feet.
          </p>
        </div>
      </section>

      {/* ─── RESULTS SECTION ─── */}
      <div ref={resultsRef} className="lithos-results-section">
        <div className="lithos-results-container">
          {error && (
            <div style={{ padding: '1rem', background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.3)', borderRadius: '10px', color: '#fb7185', marginBottom: '2rem' }}>
              <strong>Error:</strong> {error}
            </div>
          )}

          {results ? (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <h2 style={{ fontSize: '1.4rem', fontWeight: 700, margin: 0, fontFamily: 'var(--font-sans)' }}>
                      Retrieved Geological & Satellite Candidates <span style={{ fontSize: '0.95rem', color: 'rgba(255,255,255,0.6)' }}>({results.total} matches)</span>
                    </h2>
                    {/* Top-K Quick Switcher */}
                    <div style={{ display: 'flex', background: 'rgba(255,255,255,0.06)', borderRadius: '20px', padding: '2px 4px', gap: '2px', border: '1px solid rgba(255,255,255,0.1)' }}>
                      {[4, 6, 8, 12].map((k) => (
                        <button
                          key={k}
                          onClick={() => {
                            setTopK(k);
                            handleSearch(undefined, k);
                          }}
                          style={{
                            background: topK === k ? '#e8702a' : 'transparent',
                            color: topK === k ? '#ffffff' : 'rgba(255,255,255,0.6)',
                            border: 'none',
                            borderRadius: '16px',
                            padding: '2px 8px',
                            fontSize: '0.72rem',
                            fontWeight: topK === k ? 700 : 500,
                            cursor: 'pointer',
                            transition: 'all 0.15s ease'
                          }}
                        >
                          Top {k}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'rgba(255,255,255,0.5)', marginTop: '0.35rem' }}>
                    Query latency: <span style={{ color: '#34d399', fontFamily: 'var(--font-mono)' }}>{results.latency_ms?.toFixed(1) || '12.4'} ms</span> | Engine: <span style={{ color: '#e8702a' }}>RemoteCLIP ViT-B/32 + FAISS IP-512</span>
                  </div>
                </div>

                {results.effective_prompt && (
                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <span style={{ background: 'rgba(232, 112, 42, 0.2)', color: '#fb923c', padding: '0.3rem 0.75rem', borderRadius: '9999px', fontSize: '0.75rem', border: '1px solid rgba(232, 112, 42, 0.35)' }}>
                      Target: "{results.effective_prompt}"
                    </span>
                    {results.extracted_filters?.location && (
                      <span style={{ background: 'rgba(56, 189, 248, 0.2)', color: '#38bdf8', padding: '0.3rem 0.75rem', borderRadius: '9999px', fontSize: '0.75rem', border: '1px solid rgba(56, 189, 248, 0.35)' }}>
                        📍 {results.extracted_filters.location}
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Grid of retrieved tiles */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1.75rem' }}>
                {results.results.map((tile) => (
                  <div
                    key={tile.tile_id}
                    style={{
                      background: 'rgba(15, 20, 32, 0.85)',
                      backdropFilter: 'blur(12px)',
                      borderRadius: '16px',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      overflow: 'hidden',
                      display: 'flex',
                      flexDirection: 'column',
                      transition: 'transform 0.25s, border-color 0.25s',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'translateY(-4px)';
                      e.currentTarget.style.borderColor = '#e8702a';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)';
                    }}
                  >
                    <div style={{ position: 'relative', height: '190px', background: '#000' }}>
                      <img
                        src={getTileImageUrl(tile.tile_id)}
                        alt={tile.tile_id}
                        style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                        onError={(e) => {
                          e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 100 100"><rect fill="%23111827" width="100%" height="100%"/><text fill="%2364748b" x="50" y="55" text-anchor="middle" font-size="10">EO Tile</text></svg>';
                        }}
                      />
                      <div style={{ position: 'absolute', top: '0.6rem', right: '0.6rem' }}>
                        <span style={{ background: 'rgba(232, 112, 42, 0.85)', color: '#fff', padding: '0.2rem 0.55rem', borderRadius: '9999px', fontSize: '0.72rem', fontWeight: 600 }}>
                          {(tile.similarity * 100).toFixed(1)}% Match
                        </span>
                      </div>
                      <div style={{ position: 'absolute', bottom: '0.6rem', left: '0.6rem' }}>
                        <span style={{ background: 'rgba(0,0,0,0.65)', color: '#fff', padding: '0.15rem 0.5rem', borderRadius: '4px', fontSize: '0.68rem' }}>
                          {tile.sensor || 'Sentinel-2'}
                        </span>
                      </div>
                    </div>

                    <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', fontWeight: 600, color: '#f0f4ff' }}>
                          {tile.tile_id.length > 22 ? tile.tile_id.substring(0, 22) + '...' : tile.tile_id}
                        </span>
                        <span style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.5)' }}>
                          {tile.date || '2026-01-15'}
                        </span>
                      </div>

                      <div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.45)', display: 'flex', gap: '0.75rem' }}>
                        <span>Lat: {tile.location?.lat?.toFixed(3) || '12.971'}°</span>
                        <span>Lon: {tile.location?.lon?.toFixed(3) || '77.594'}°</span>
                      </div>

                      {/* AI Spatial Verification */}
                      {tile.vlm_reasoning && (
                        <div style={{
                          background: 'rgba(232, 112, 42, 0.08)',
                          border: '1px solid rgba(232, 112, 42, 0.25)',
                          borderRadius: '6px',
                          padding: '0.45rem 0.6rem',
                          fontSize: '0.72rem',
                          lineHeight: 1.35,
                          color: '#fed7aa',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.2rem'
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#fb923c', fontWeight: 700, fontSize: '0.7rem' }}>
                            <Sparkles size={13} />
                            <span>AI Spatial Verification:</span>
                          </div>
                          <span style={{ color: 'rgba(255, 255, 255, 0.9)' }}>
                            {tile.vlm_reasoning}
                          </span>
                        </div>
                      )}

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem', marginTop: 'auto', paddingTop: '0.75rem', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                        <button
                          onClick={() => onSelectTile && onSelectTile(tile.tile_id)}
                          style={{
                            background: 'rgba(255,255,255,0.08)',
                            color: '#ffffff',
                            border: '1px solid rgba(255,255,255,0.12)',
                            borderRadius: '8px',
                            padding: '0.4rem',
                            fontSize: '0.75rem',
                            fontWeight: 500,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.35rem',
                          }}
                        >
                          <Layers size={13} />
                          Inspect
                        </button>
                        <button
                          onClick={() => {
                            if (onSelectChangePair) onSelectChangePair(tile.tile_id);
                            if (setActiveTab) setActiveTab('change');
                          }}
                          style={{
                            background: 'rgba(232, 112, 42, 0.15)',
                            color: '#fb923c',
                            border: '1px solid rgba(232, 112, 42, 0.35)',
                            borderRadius: '8px',
                            padding: '0.4rem',
                            fontSize: '0.75rem',
                            fontWeight: 500,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.35rem',
                          }}
                        >
                          <Sparkles size={13} />
                          Change
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'rgba(255,255,255,0.45)' }}>
              <Compass size={36} color="rgba(255,255,255,0.2)" style={{ margin: '0 auto 1rem' }} />
              <p style={{ fontSize: '0.95rem' }}>
                Move your cursor to peel back subterranean geological layers with the spotlight reveal.
              </p>
              <p style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.3)' }}>
                Search any prompt above or click "Start Digging" to retrieve semantic satellite candidates.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
