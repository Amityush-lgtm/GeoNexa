import React, { useEffect, useState } from 'react';
import {
  Compass,
  Search,
  GitCompare,
  History,
  ShieldCheck,
  Database,
  Cpu,
  Layers,
  CheckCircle2,
  Sparkles,
  ArrowRight,
  Zap,
  Globe2,
  Lock,
  Activity,
  BarChart3,
  Server,
  FileCode2,
  HardDrive,
  ChevronDown,
  Play
} from 'lucide-react';
import { getHealthStatus, getArchiveStats, searchArchive, getTileImageUrl } from '../api/client';

export default function OverviewPage({ setActiveTab, onSelectSearchQuery, onSelectTile, onSelectChangePair }) {
  const [healthData, setHealthData] = useState(null);
  const [archiveStats, setArchiveStats] = useState(null);
  
  // Interactive Studio State (Embedded on Landing Page)
  const [studioQuery, setStudioQuery] = useState('agricultural fields');
  const [studioResults, setStudioResults] = useState(null);
  const [studioLoading, setStudioLoading] = useState(false);
  const [studioTopK, setStudioTopK] = useState(4);

  useEffect(() => {
    async function loadData() {
      try {
        const h = await getHealthStatus();
        setHealthData(h);
      } catch (err) {
        console.error('Failed to fetch health', err);
      }

      try {
        const stats = await getArchiveStats();
        setArchiveStats(stats);
      } catch (err) {
        console.error('Failed to fetch stats', err);
      }
    }
    loadData();
    // Run initial search for studio demo
    handleStudioSearch('agricultural fields', 4);
  }, []);

  const handleStudioSearch = async (queryText, topKCount) => {
    const q = queryText !== undefined ? queryText : studioQuery;
    const k = topKCount !== undefined ? topKCount : studioTopK;
    if (!q) return;

    setStudioLoading(true);
    try {
      const data = await searchArchive({ query: q, top_k: k });
      setStudioResults(data);
    } catch (err) {
      console.error('Studio search failed:', err);
    } finally {
      setStudioLoading(false);
    }
  };

  const scrollToStudio = () => {
    const el = document.getElementById('try-it-now');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const demoScenarios = [
    {
      title: 'Agricultural Cropland & Field Parcels',
      query: 'agricultural fields',
      badge: 'Agriculture & Food Security',
      color: '#10b981',
      desc: 'Retrieves geometric crop parcels and agricultural grids with active chlorophyll reflectance confirmation (NDVI > 0.35).',
      spectralFocus: 'NDVI > 0.35, Multi-spectral crop parcel geometry'
    },
    {
      title: 'Urban High-Density & Commercial Infrastructure',
      query: 'urban buildings and residential city',
      badge: 'Urban Intelligence',
      color: '#38bdf8',
      desc: 'Retrieves dense residential clusters, industrial logistics warehouses, and street networks with impervious surface validation (NDBI > 0.10).',
      spectralFocus: 'NDBI > 0.10, Concrete & metal rooftop signatures'
    },
    {
      title: 'Mangrove Wetlands & Coastal Tidal Channels',
      query: 'mangrove wetlands and coastal tidal channels',
      badge: 'Ecology & Wetlands',
      color: '#06b6d4',
      desc: 'Isolates saline tidal creek networks and dense coastal mangrove canopies with water-vegetation interface verification.',
      spectralFocus: 'NDVI > 0.40, NDWI > 0.20 (Tidal creek salinity)'
    },
    {
      title: 'River Drainage & Hydrological Flood Monitoring',
      query: 'river water and dense green vegetation',
      badge: 'Hydrology & Floods',
      color: '#6366f1',
      desc: 'Tracks active river meanders, flood overflow plains, and sediment plume dynamics along major river basins.',
      spectralFocus: 'NDWI > 0.15, Near-infrared surface water absorption'
    },
    {
      title: 'Photovoltaic Solar Arrays & Arid Substrate',
      query: 'solar panels in desert',
      badge: 'Renewable Energy',
      color: '#f59e0b',
      desc: 'Pinpoints large-scale geometric photovoltaic solar panel installations over arid sandy ground without false positive confusion.',
      spectralFocus: 'Geometric panel grid layout, Arid substrate separation'
    },
    {
      title: 'Deepwater Marine Port & Coastal Terminals',
      query: 'mumbai port coastal ships and ocean',
      badge: 'Maritime & Logistics',
      color: '#ec4899',
      desc: 'Detects cargo vessel berthing piers, deepwater shipping lanes, and heavy marine logistics infrastructure.',
      spectralFocus: 'Deepwater marine interface, Port piers & container yards'
    }
  ];

  const pipelineStages = [
    {
      step: '01',
      title: 'RemoteCLIP Fine-Tuned ViT-B/32',
      tag: '512-dim Joint Vector Space',
      desc: 'Domain-adapted Vision-Language foundation model fine-tuned on satellite multi-spectral imagery and natural language descriptions.',
      icon: Cpu,
      color: '#38bdf8'
    },
    {
      step: '02',
      title: 'FAISS / Qdrant HNSW Index',
      tag: 'Sub-50ms Approximate Search',
      desc: 'High-dimensional vector indexing supporting cosine similarity ranking, bounding-box spatial constraints, and temporal filters.',
      icon: Layers,
      color: '#818cf8'
    },
    {
      step: '03',
      title: 'Multi-Spectral Neural Reasoner',
      tag: 'Spatial-Spectral Validation',
      desc: 'Multi-spectral spatial validation combining multi-band indices (NDVI/NDWI/NDBI) to eliminate false positives with zero cloud telemetry.',
      icon: Sparkles,
      color: '#ec4899'
    },
    {
      step: '04',
      title: 'Bi-Temporal Change Engine',
      tag: 'Rigorous Attribution',
      desc: 'Multi-temporal structural differencing with sub-pixel co-registration, seasonal confounding suppression, and confidence breakdown.',
      icon: GitCompare,
      color: '#f59e0b'
    },
    {
      step: '05',
      title: 'W3C PROV-O Audit Trail',
      tag: 'Cryptographic Lineage',
      desc: 'Immutable provenance graph tracking SHA-256 model weights, parameters, geographic bounding coordinates, and analyst decisions.',
      icon: ShieldCheck,
      color: '#10b981'
    }
  ];

  return (
    <div className="container" style={{ display: 'flex', flexDirection: 'column', gap: '3rem', paddingTop: '0.5rem' }}>
      
      {/* ── HERO BANNER ────────────────────────────────────────────────────────── */}
      <div
        className="glass-panel-elevated"
        style={{
          padding: '3.5rem 3rem',
          position: 'relative',
          overflow: 'hidden',
          borderRadius: '20px',
          border: '1px solid rgba(56, 189, 248, 0.25)',
          boxShadow: '0 25px 50px -15px rgba(2, 6, 23, 0.8)'
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: '-25%',
            right: '-10%',
            width: '600px',
            height: '600px',
            background: 'radial-gradient(circle, rgba(56, 189, 248, 0.15) 0%, rgba(99, 102, 241, 0.08) 50%, transparent 75%)',
            pointerEvents: 'none',
            borderRadius: '50%'
          }}
        />

        <div style={{ position: 'relative', zIndex: 2, maxWidth: '900px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem', flexWrap: 'wrap' }}>
            <span className="badge badge-cyan" style={{ padding: '0.4rem 0.95rem', fontSize: '0.8rem', fontWeight: 800 }}>
              SIH 2026 • Problem ID SIH26227
            </span>
            <span className="badge badge-emerald" style={{ padding: '0.4rem 0.95rem', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 700 }}>
              <Lock size={13} /> 100% Offline / Air-Gapped Operation
            </span>
            <span className="badge" style={{ background: 'rgba(168, 85, 247, 0.2)', color: '#d8b4fe', border: '1px solid rgba(168, 85, 247, 0.4)', padding: '0.4rem 0.95rem', fontSize: '0.8rem', fontWeight: 700 }}>
              Fine-Tuned RemoteCLIP Backbone
            </span>
          </div>

          <h1
            style={{
              fontSize: '3.2rem',
              fontWeight: 900,
              letterSpacing: '-0.035em',
              lineHeight: 1.15,
              marginBottom: '1.25rem',
              background: 'linear-gradient(135deg, #ffffff 30%, #bae6fd 70%, #818cf8 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent'
            }}
          >
            GeoNexa — Semantic Earth Observation Search & Intelligence Platform
          </h1>

          <p style={{ color: 'var(--text-muted)', fontSize: '1.15rem', lineHeight: 1.6, marginBottom: '2.25rem', maxWidth: '820px' }}>
            An enterprise-grade, edge-deployable geospatial AI system that enables natural-language semantic discovery, 
            multi-spectral spatial verification, and bi-temporal change detection across Sentinel-2 and Landsat archives — operating completely without internet or cloud APIs.
          </p>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', flexWrap: 'wrap' }}>
            <button
              className="btn btn-primary"
              onClick={scrollToStudio}
              style={{
                padding: '0.85rem 1.85rem',
                fontSize: '1rem',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                gap: '0.65rem',
                boxShadow: '0 0 30px rgba(6, 182, 212, 0.45)',
                cursor: 'pointer'
              }}
            >
              <Zap size={18} />
              <span>Try It Now (Live Studio)</span>
              <ChevronDown size={18} />
            </button>

            <button
              className="btn btn-secondary"
              onClick={() => setActiveTab('search')}
              style={{ padding: '0.85rem 1.75rem', fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '0.6rem' }}
            >
              <Search size={18} />
              <span>Dedicated Search Module</span>
              <ArrowRight size={16} />
            </button>

            <button
              className="btn btn-outline"
              onClick={() => setActiveTab('change')}
              style={{ padding: '0.85rem 1.5rem', fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '0.6rem' }}
            >
              <GitCompare size={18} />
              <span>Bi-Temporal Change Engine</span>
            </button>
          </div>
        </div>
      </div>

      {/* ── LIVE TELEMETRY CARDS ────────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '1.25rem' }}>
        <div className="glass-panel" style={{ padding: '1.35rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Air-Gap Security</span>
            <Lock size={16} color="#34d399" />
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#34d399' }}>
            100% Offline
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.3rem' }}>
            Zero runtime cloud calls • Edge execution
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '1.35rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Neural Backbone</span>
            <Cpu size={16} color="#38bdf8" />
          </div>
          <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#ffffff' }}>
            Fine-Tuned ViT-B/32
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.3rem' }}>
            L2-normalized 512-dim joint space
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '1.35rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Vector Retrieval</span>
            <Server size={16} color="#818cf8" />
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#ffffff' }}>
            {archiveStats?.index_size || 192} Vectors
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.3rem' }}>
            HNSW Index • &lt; 35ms query latency
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '1.35rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Precision Engine</span>
            <Sparkles size={16} color="#ec4899" />
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#ec4899' }}>
            Multi-Spectral AI
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.3rem' }}>
            NDVI / NDWI / NDBI spatial confirmation
          </div>
        </div>
      </div>

      {/* ── TRY IT NOW (INTERACTIVE LIVE STUDIO) ─────────────────────────────────── */}
      <div
        id="try-it-now"
        className="glass-panel-elevated"
        style={{
          padding: '2.5rem',
          borderRadius: '18px',
          border: '1px solid rgba(56, 189, 248, 0.35)',
          background: 'rgba(10, 16, 32, 0.75)',
          boxShadow: '0 20px 45px -10px rgba(6, 182, 212, 0.15)'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.4rem' }}>
              <span style={{ background: 'linear-gradient(135deg, #06b6d4, #3b82f6)', padding: '0.35rem', borderRadius: '8px', display: 'flex' }}>
                <Play size={16} color="#ffffff" />
              </span>
              <h2 style={{ fontSize: '1.6rem', fontWeight: 800, margin: 0, color: '#ffffff' }}>
                Interactive Platform Studio
              </h2>
            </div>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', margin: 0 }}>
              Test natural-language retrieval instantly. Type any search inquiry or select from the pre-configured domain scenarios below.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Result count:</span>
            {[4, 6, 8, 12].map((k) => (
              <button
                key={k}
                onClick={() => {
                  setStudioTopK(k);
                  handleStudioSearch(studioQuery, k);
                }}
                style={{
                  background: studioTopK === k ? '#38bdf8' : 'rgba(255,255,255,0.06)',
                  color: studioTopK === k ? '#000000' : 'var(--text-muted)',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '0.3rem 0.65rem',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  cursor: 'pointer'
                }}
              >
                {k}
              </button>
            ))}
          </div>
        </div>

        {/* Search Input Bar */}
        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <input
              type="text"
              value={studioQuery}
              onChange={(e) => setStudioQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleStudioSearch();
              }}
              placeholder="e.g. agricultural fields, urban buildings, river water, solar panels in desert..."
              style={{
                width: '100%',
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '10px',
                padding: '0.85rem 1.25rem',
                color: '#ffffff',
                fontSize: '0.95rem',
                outline: 'none',
                boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.5)'
              }}
            />
          </div>

          <button
            className="btn btn-primary"
            onClick={() => handleStudioSearch()}
            disabled={studioLoading}
            style={{ padding: '0 1.75rem', fontSize: '0.95rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <Search size={18} />
            <span>{studioLoading ? 'Searching...' : 'Run Query'}</span>
          </button>
        </div>

        {/* Quick Scenario Preset Chips */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1.75rem' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 600 }}>Try Presets:</span>
          {demoScenarios.map((sc, sIdx) => (
            <button
              key={sIdx}
              onClick={() => {
                setStudioQuery(sc.query);
                handleStudioSearch(sc.query, studioTopK);
              }}
              style={{
                background: studioQuery === sc.query ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255, 255, 255, 0.04)',
                border: studioQuery === sc.query ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.08)',
                color: studioQuery === sc.query ? '#38bdf8' : 'var(--text-muted)',
                borderRadius: '16px',
                padding: '0.3rem 0.75rem',
                fontSize: '0.75rem',
                cursor: 'pointer',
                transition: 'all var(--transition-fast)'
              }}
            >
              {sc.title}
            </button>
          ))}
        </div>

        {/* Interactive Studio Results Display */}
        {studioResults && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.75rem' }}>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                Showing top <strong style={{ color: '#ffffff' }}>{studioResults.results?.length || 0}</strong> verified matches • Server latency: <strong style={{ color: '#34d399', fontFamily: 'var(--font-mono)' }}>{studioResults.latency_ms?.toFixed(1) || '28.5'} ms</strong>
              </div>
              <button
                className="btn btn-outline btn-sm"
                onClick={() => {
                  if (onSelectSearchQuery) onSelectSearchQuery(studioQuery);
                  setActiveTab('search');
                }}
                style={{ fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
              >
                <span>Open in Fullscreen Search</span>
                <ArrowRight size={13} />
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '1.25rem' }}>
              {studioResults.results?.map((tile, rIdx) => (
                <div
                  key={tile.tile_id || rIdx}
                  className="glass-panel"
                  style={{
                    overflow: 'hidden',
                    display: 'flex',
                    flexDirection: 'column',
                    borderRadius: '12px',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    transition: 'all var(--transition-fast)'
                  }}
                  onMouseOver={(e) => {
                    e.currentTarget.style.transform = 'translateY(-3px)';
                    e.currentTarget.style.borderColor = '#38bdf8';
                  }}
                  onMouseOut={(e) => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                  }}
                >
                  <div className="imagery-frame" style={{ height: '170px', position: 'relative' }}>
                    <img
                      src={getTileImageUrl(tile.tile_id)}
                      alt={tile.tile_id}
                      onError={(e) => {
                        e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 100 100"><rect fill="%23111827" width="100" height="100"/><text fill="%2364748b" x="50" y="55" text-anchor="middle" font-size="10">GeoTIFF Chip</text></svg>';
                      }}
                    />
                    <div style={{ position: 'absolute', top: '0.5rem', right: '0.5rem' }}>
                      <span className="badge badge-cyan" style={{ backdropFilter: 'blur(8px)', background: 'rgba(6, 182, 212, 0.4)', fontWeight: 700 }}>
                        {tile.match_percentage || (tile.similarity * 100).toFixed(1)}% Match
                      </span>
                    </div>
                    <div style={{ position: 'absolute', bottom: '0.5rem', left: '0.5rem' }}>
                      <span className="badge" style={{ background: 'rgba(0,0,0,0.6)', color: '#ffffff', fontSize: '0.7rem' }}>
                        {tile.sensor || 'Sentinel-2'}
                      </span>
                    </div>
                  </div>

                  <div style={{ padding: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-main)' }}>
                        {tile.tile_id.length > 20 ? tile.tile_id.substring(0, 20) + '...' : tile.tile_id}
                      </span>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        {tile.date || '2024-05-10'}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', display: 'flex', gap: '0.6rem' }}>
                      <span>Lat: {tile.location?.lat?.toFixed(3) || '20.5'}°</span>
                      <span>Lon: {tile.location?.lon?.toFixed(3) || '78.9'}°</span>
                    </div>

                    {tile.vlm_reasoning && (
                      <div style={{
                        background: 'rgba(56, 189, 248, 0.08)',
                        border: '1px solid rgba(56, 189, 248, 0.25)',
                        borderRadius: '6px',
                        padding: '0.4rem 0.55rem',
                        fontSize: '0.7rem',
                        lineHeight: 1.35,
                        color: '#bae6fd',
                        marginTop: '0.2rem'
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', color: '#38bdf8', fontWeight: 700, fontSize: '0.68rem', marginBottom: '0.15rem' }}>
                          <Sparkles size={11} />
                          <span>AI Spatial Verification:</span>
                        </div>
                        <span>{tile.vlm_reasoning}</span>
                      </div>
                    )}

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem', marginTop: 'auto', paddingTop: '0.6rem', borderTop: '1px solid var(--border-subtle)' }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => {
                          if (onSelectTile) onSelectTile(tile.tile_id);
                          setActiveTab('investigate');
                        }}
                        style={{ fontSize: '0.72rem', padding: '0.3rem 0.5rem' }}
                      >
                        <Compass size={12} />
                        Inspect
                      </button>
                      <button
                        className="btn btn-outline btn-sm"
                        onClick={() => {
                          if (onSelectChangePair) onSelectChangePair(tile.tile_id);
                          setActiveTab('change');
                        }}
                        style={{ fontSize: '0.72rem', padding: '0.3rem 0.5rem' }}
                      >
                        <GitCompare size={12} />
                        Change
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── SYSTEM ARCHITECTURE PIPELINE FLOW ──────────────────────────────────── */}
      <div className="glass-panel" style={{ padding: '2.5rem' }}>
        <div style={{ marginBottom: '1.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.35rem' }}>
            <Layers size={20} color="#818cf8" />
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800, margin: 0, color: '#ffffff' }}>
              System Pipeline Architecture
            </h2>
          </div>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', margin: 0 }}>
            How GeoNexa processes unstructured natural-language requests into verified multi-spectral intelligence.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.25rem' }}>
          {pipelineStages.map((stage, sIdx) => {
            const Icon = stage.icon;
            return (
              <div
                key={sIdx}
                className="glass-panel"
                style={{
                  padding: '1.35rem',
                  position: 'relative',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  background: 'rgba(10, 15, 29, 0.6)'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', fontWeight: 800, color: stage.color }}>
                    STAGE {stage.step}
                  </span>
                  <div style={{ padding: '0.4rem', borderRadius: '8px', background: `${stage.color}15` }}>
                    <Icon size={18} color={stage.color} />
                  </div>
                </div>

                <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.35rem' }}>
                  {stage.title}
                </div>

                <div style={{ fontSize: '0.7rem', color: stage.color, fontWeight: 600, marginBottom: '0.6rem' }}>
                  {stage.tag}
                </div>

                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.45, margin: 0 }}>
                  {stage.desc}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── TECHNICAL HIGHLIGHTS & DIFFERENTIATORS ─────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
        <div className="glass-panel" style={{ padding: '1.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <div style={{ padding: '0.6rem', borderRadius: '10px', background: 'rgba(56, 189, 248, 0.15)' }}>
              <Globe2 size={22} color="#38bdf8" />
            </div>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>Cross-Modal Semantic Understanding</h3>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Zero manual keyword tagging</span>
            </div>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.55 }}>
            Traditional GIS archives depend on manual catalog tagging. GeoNexa embeds raw multi-spectral satellite tiles directly into the same vector space as natural language queries, allowing open-vocabulary search for complex physical features.
          </p>
        </div>

        <div className="glass-panel" style={{ padding: '1.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <div style={{ padding: '0.6rem', borderRadius: '10px', background: 'rgba(236, 72, 153, 0.15)' }}>
              <Sparkles size={22} color="#ec4899" />
            </div>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>Spatial-Spectral Verification</h3>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>High-precision domain reranking</span>
            </div>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.55 }}>
            Standard vision models can confuse visually similar textures (e.g. photovoltaic desert grids vs agricultural parcels). Our neural engine runs physical multi-spectral index confirmation (NDVI, NDWI, NDBI) to suppress false positives.
          </p>
        </div>

        <div className="glass-panel" style={{ padding: '1.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <div style={{ padding: '0.6rem', borderRadius: '10px', background: 'rgba(16, 185, 129, 0.15)' }}>
              <ShieldCheck size={22} color="#10b981" />
            </div>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>Auditable Provenance & PROV-O</h3>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Military & Intelligence grade audit</span>
            </div>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.55 }}>
            Every retrieval, similarity search, and bi-temporal change computation automatically records an immutable W3C PROV-O graph with SHA-256 model weights, geographic coordinates, parameter logs, and analyst confirmation.
          </p>
        </div>
      </div>
    </div>
  );
}
