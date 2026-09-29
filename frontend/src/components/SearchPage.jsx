import React, { useState } from 'react';
import { Search, Sparkles, Filter, Calendar, Satellite, Sliders, ExternalLink, ArrowRight, Shield, Layers } from 'lucide-react';
import { searchArchive, routeQuery, getTileImageUrl } from '../api/client';

export default function SearchPage({ onSelectTile, onSelectChangePair, onSelectProvenance, setActiveTab }) {
  const [query, setQuery] = useState('newly built structures near a river');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  // Filters
  const [showFilters, setShowFilters] = useState(false);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [sensor, setSensor] = useState('');
  const [topK, setTopK] = useState(12);

  // Intent suggestion
  const [intentSuggestion, setIntentSuggestion] = useState(null);

  const sampleQueries = [
    'newly built structures near a river',
    'dense forest canopy and dark green vegetation',
    'agricultural crop fields and farmland',
    'coastal port docks and cargo containers',
    'asphalt road and transportation corridor',
  ];

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
        // silently ignore suggestion errors
      }
    } else {
      setIntentSuggestion(null);
    }
  };

  const handleSearch = async (overrideQuery) => {
    const q = overrideQuery || query;
    if (!q) return;

    setLoading(true);
    setError(null);

    try {
      const payload = {
        query: q,
        top_k: parseInt(topK, 10),
      };
      if (dateFrom) payload.date_from = dateFrom;
      if (dateTo) payload.date_to = dateTo;
      if (sensor) payload.sensor = sensor;

      const data = await searchArchive(payload);
      setResults(data);
    } catch (err) {
      setError(err.message || 'Error executing search');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Search Header Banner */}
      <div className="glass-panel-elevated" style={{ padding: '2.5rem', textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute',
          top: '-50%',
          left: '50%',
          transform: 'translateX(-50%)',
          width: '600px',
          height: '300px',
          background: 'radial-gradient(circle, rgba(6, 182, 212, 0.15) 0%, transparent 70%)',
          pointerEvents: 'none'
        }} />

        <h1 style={{ fontSize: '2.2rem', fontWeight: 800, letterSpacing: '-0.03em', marginBottom: '0.75rem', background: 'linear-gradient(135deg, #ffffff 40%, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          Semantic Earth Observation Search
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '1rem', maxWidth: '680px', margin: '0 auto 1.75rem' }}>
          Natural-language indexing and similarity retrieval across multi-sensor satellite imagery archives without internet dependency.
        </p>

        {/* Query Input Box */}
        <div style={{ maxWidth: '850px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            background: 'var(--bg-surface-elevated)',
            borderRadius: '12px',
            padding: '0.4rem 0.6rem 0.4rem 1.25rem',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            boxShadow: '0 8px 30px rgba(0, 0, 0, 0.4), var(--border-glow)',
          }}>
            <Search size={20} color="#38bdf8" style={{ marginRight: '0.75rem', flexShrink: 0 }} />
            <input
              type="text"
              value={query}
              onChange={handleQueryChange}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Type an intelligence query, e.g. 'newly built structures near a river'..."
              style={{
                width: '100%',
                background: 'transparent',
                border: 'none',
                color: '#ffffff',
                fontSize: '1rem',
                outline: 'none',
                fontFamily: 'var(--font-sans)',
              }}
            />
            <div style={{ display: 'flex', gap: '0.5rem', flexShrink: 0 }}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setShowFilters(!showFilters)}
                style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
              >
                <Filter size={14} />
                Filters
              </button>
              <button
                className="btn btn-primary"
                onClick={() => handleSearch()}
                disabled={loading}
              >
                {loading ? 'Searching...' : 'Search'}
                <ArrowRight size={16} />
              </button>
            </div>
          </div>

          {/* Natural Language Intent Smart Routing Banner */}
          {intentSuggestion && (
            <div style={{
              background: 'rgba(99, 102, 241, 0.15)',
              border: '1px solid rgba(99, 102, 241, 0.4)',
              borderRadius: '8px',
              padding: '0.5rem 1rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '0.8rem',
              color: '#c7d2fe'
            }}>
              <span>
                💡 Query classified as <strong>{intentSuggestion.intent}</strong> ({Math.round(intentSuggestion.confidence * 100)}% confidence).
              </span>
              <button
                className="btn btn-outline btn-sm"
                onClick={() => setActiveTab(intentSuggestion.suggested_action)}
                style={{ padding: '0.2rem 0.6rem', fontSize: '0.75rem' }}
              >
                Open {intentSuggestion.suggested_action.toUpperCase()} Mode
              </button>
            </div>
          )}

          {/* Filter Drawer */}
          {showFilters && (
            <div className="glass-panel" style={{ padding: '1rem 1.25rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', textAlign: 'left' }}>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.3rem' }}>Acquisition From</label>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  style={{ width: '100%', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '0.4rem', color: '#ffffff', fontSize: '0.8rem' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.3rem' }}>Acquisition To</label>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  style={{ width: '100%', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '0.4rem', color: '#ffffff', fontSize: '0.8rem' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.3rem' }}>Sensor</label>
                <select
                  value={sensor}
                  onChange={(e) => setSensor(e.target.value)}
                  style={{ width: '100%', background: 'var(--bg-surface-elevated)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '0.4rem', color: '#ffffff', fontSize: '0.8rem' }}
                >
                  <option value="">All Sensors</option>
                  <option value="Sentinel-2">Sentinel-2 (MSI)</option>
                  <option value="Landsat-8">Landsat-8 (OLI)</option>
                </select>
              </div>
              <div>
                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.3rem' }}>Top Results (K)</label>
                <select
                  value={topK}
                  onChange={(e) => setTopK(e.target.value)}
                  style={{ width: '100%', background: 'var(--bg-surface-elevated)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '0.4rem', color: '#ffffff', fontSize: '0.8rem' }}
                >
                  <option value="6">6 Results</option>
                  <option value="12">12 Results</option>
                  <option value="24">24 Results</option>
                  <option value="48">48 Results</option>
                </select>
              </div>
            </div>
          )}

          {/* Quick query chips */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'center', marginTop: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Try queries:</span>
            {sampleQueries.map((sq, i) => (
              <button
                key={i}
                onClick={() => {
                  setQuery(sq);
                  handleSearch(sq);
                }}
                style={{
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '16px',
                  padding: '0.25rem 0.65rem',
                  fontSize: '0.75rem',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  transition: 'all var(--transition-fast)'
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.color = '#38bdf8';
                  e.currentTarget.style.borderColor = 'rgba(56, 189, 248, 0.4)';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.color = 'var(--text-muted)';
                  e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)';
                }}
              >
                {sq}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Error Notice */}
      {error && (
        <div style={{ padding: '1rem', background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.3)', borderRadius: '10px', color: '#fb7185' }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Results Header */}
      {results && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <div>
              <h2 style={{ fontSize: '1.3rem', fontWeight: 700 }}>
                Retrieved Tile Candidates <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>({results.total} matches)</span>
              </h2>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '0.2rem' }}>
                Query latency: <span style={{ color: '#34d399', fontFamily: 'var(--font-mono)' }}>{results.latency_ms.toFixed(1)} ms</span> | Provenance: <span style={{ color: '#38bdf8', cursor: 'pointer', textDecoration: 'underline' }} onClick={() => onSelectProvenance(results.results[0]?.provenance_id)}>{results.results[0]?.provenance_id || 'N/A'}</span>
              </div>
            </div>
          </div>

          {/* Results Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1.5rem' }}>
            {results.results.map((tile) => (
              <div
                key={tile.tile_id}
                className="glass-panel"
                style={{
                  overflow: 'hidden',
                  display: 'flex',
                  flexDirection: 'column',
                  transition: 'transform var(--transition-smooth), border-color var(--transition-smooth)',
                  cursor: 'pointer'
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.transform = 'translateY(-4px)';
                  e.currentTarget.style.borderColor = 'var(--accent-sky)';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.borderColor = 'var(--border-subtle)';
                }}
              >
                {/* Tile Image Thumbnail */}
                <div className="imagery-frame" style={{ height: '190px' }}>
                  <img
                    src={getTileImageUrl(tile.tile_id)}
                    alt={tile.tile_id}
                    onError={(e) => {
                      e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 100 100"><rect fill="%23111827" width="100" height="100"/><text fill="%2364748b" x="50" y="55" text-anchor="middle" font-size="10">GeoTIFF Chip</text></svg>';
                    }}
                  />
                  {/* Similarity Badge */}
                  <div style={{ position: 'absolute', top: '0.6rem', right: '0.6rem' }}>
                    <span className="badge badge-cyan" style={{ backdropFilter: 'blur(8px)', background: 'rgba(6, 182, 212, 0.35)' }}>
                      {(tile.similarity * 100).toFixed(1)}% Match
                    </span>
                  </div>
                  {/* Sensor Badge */}
                  <div style={{ position: 'absolute', bottom: '0.6rem', left: '0.6rem' }}>
                    <span className="badge" style={{ background: 'rgba(0,0,0,0.6)', color: '#ffffff', fontSize: '0.7rem' }}>
                      {tile.sensor || 'Sentinel-2'}
                    </span>
                  </div>
                </div>

                {/* Metadata Details */}
                <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.6rem', flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-main)' }}>
                      {tile.tile_id.length > 22 ? tile.tile_id.substring(0, 22) + '...' : tile.tile_id}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {tile.date || '2026-01-15'}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', display: 'flex', gap: '0.75rem' }}>
                    <span>Lat: {tile.location.lat.toFixed(3)}°</span>
                    <span>Lon: {tile.location.lon.toFixed(3)}°</span>
                  </div>

                  {/* Actions */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem', marginTop: 'auto', paddingTop: '0.6rem', borderTop: '1px solid var(--border-subtle)' }}>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => onSelectTile(tile.tile_id)}
                      style={{ fontSize: '0.75rem' }}
                    >
                      <Layers size={13} />
                      Inspect
                    </button>
                    <button
                      className="btn btn-outline btn-sm"
                      onClick={() => {
                        onSelectChangePair(tile.tile_id);
                        setActiveTab('change');
                      }}
                      style={{ fontSize: '0.75rem' }}
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
      )}
    </div>
  );
}
