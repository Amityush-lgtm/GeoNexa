import React, { useState, useEffect } from 'react';
import { History, ArrowRight, Layers, Sparkles } from 'lucide-react';
import { searchSimilar, getTileImageUrl } from '../api/client';

export default function SimilarPage({ queryTileId, onSelectTile, onSelectChangePair, setActiveTab }) {
  const [tileId, setTileId] = useState(queryTileId || '');
  const [topK, setTopK] = useState(12);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (queryTileId) {
      setTileId(queryTileId);
      handleSearch(queryTileId);
    }
  }, [queryTileId]);

  const handleSearch = async (overrideId) => {
    const id = overrideId || tileId;
    if (!id) return;

    setLoading(true);
    setError(null);

    try {
      const data = await searchSimilar(id, parseInt(topK, 10));
      setResults(data);
    } catch (err) {
      setError(err.message || 'Similarity search failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header Banner */}
      <div className="glass-panel-elevated" style={{ padding: '1.5rem 2rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <History size={22} color="var(--accent-indigo)" />
            Site-to-Site Visual Similarity Discovery
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Find geographically dispersed locations exhibiting identical visual and structural patterns via deep embedding vector matching.
          </p>
        </div>

        {/* Query Input */}
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <input
            type="text"
            value={tileId}
            onChange={(e) => setTileId(e.target.value)}
            placeholder="Enter reference tile ID (e.g. DELHI_S2_20260115_T1_x01_y01)..."
            style={{ flex: 1, background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '0.55rem 0.85rem', color: '#ffffff', fontSize: '0.85rem', fontFamily: 'var(--font-mono)' }}
          />
          <select
            value={topK}
            onChange={(e) => setTopK(e.target.value)}
            style={{ background: 'var(--bg-surface-elevated)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '0.55rem', color: '#ffffff', fontSize: '0.85rem' }}
          >
            <option value="6">Top 6</option>
            <option value="12">Top 12</option>
            <option value="24">Top 24</option>
          </select>
          <button
            className="btn btn-primary"
            onClick={() => handleSearch()}
            disabled={loading || !tileId}
          >
            {loading ? 'Finding...' : 'Discover Similar'}
          </button>
        </div>
      </div>

      {error && <div style={{ padding: '1rem', background: 'rgba(244,63,94,0.15)', color: '#fb7185', borderRadius: '8px' }}>{error}</div>}

      {/* Results */}
      {results && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
              Discovered Similar Sites ({results.total} matches)
            </h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Query Latency: <span style={{ color: '#34d399', fontFamily: 'var(--font-mono)' }}>{results.latency_ms.toFixed(1)} ms</span>
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1.5rem' }}>
            {results.results.map((tile) => (
              <div
                key={tile.tile_id}
                className="glass-panel"
                style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}
              >
                <div className="imagery-frame" style={{ height: '180px' }}>
                  <img src={getTileImageUrl(tile.tile_id)} alt={tile.tile_id} />
                  <div style={{ position: 'absolute', top: '0.5rem', right: '0.5rem' }}>
                    <span className="badge badge-emerald">
                      {(tile.similarity * 100).toFixed(1)}% Match
                    </span>
                  </div>
                </div>

                <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1 }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', fontWeight: 600 }}>
                    {tile.tile_id}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Acquired: {tile.date || '2026-01-15'} | Lat: {tile.location.lat.toFixed(3)}°, Lon: {tile.location.lon.toFixed(3)}°
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem', marginTop: 'auto', paddingTop: '0.6rem', borderTop: '1px solid var(--border-subtle)' }}>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => onSelectTile(tile.tile_id)}
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
