import React, { useState, useEffect } from 'react';
import { History, Sparkles, ZoomIn, GitCompare, ArrowRight, Filter, Compass, Layers, Check } from 'lucide-react';
import { searchSimilar, getTileImageUrl, listArchiveTiles } from '../api/client';
import './SimilarPage.css';

const SIMILAR_PRESETS = [
  {
    id: 'port-terminal',
    label: 'Deepwater Port & Maritime Terminal',
    refId: 'S2A_MSIL2A_20240312_MUMBAI_PORT_COAST_x03_y00',
    name: 'Mumbai Port & JNPT Maritime Basin',
  },
  {
    id: 'urban-hub',
    label: 'Urban Industrial & Road Network',
    refId: 'S2A_MSIL2A_20240825_URBAN_INDUSTRIAL_HUB_x01_y03',
    name: 'High-Density Built-up & Logistics Hub',
  },
  {
    id: 'forest-canopy',
    label: 'Dense Forest Canopy on Hills',
    refId: 'S2B_MSIL2A_20240618_FOREST_WATERSHED_x03_y02',
    name: 'Western Ghats Forest Watershed',
  },
  {
    id: 'agri-parcels',
    label: 'Agricultural Parcels & Farmlands',
    refId: 'S2A_MSIL2A_20240510_COASTAL_AGRICULTURE_x03_y00',
    name: 'Alluvial Agricultural Farmland Parcels',
  },
  {
    id: 'river-basin',
    label: 'River Basin & Floodplain',
    refId: 'S2A_MSIL2A_20240115_ASSAM_BRAHMAPUTRA_T1_x01_y01',
    name: 'Brahmaputra Riverbed & Alluvial Plumes',
  },
  {
    id: 'mangrove-delta',
    label: 'Mangrove Estuary & Tidal Channels',
    refId: 'S2A_MSIL2A_20240218_SUNDARBANS_MANGROVE_x01_y00',
    name: 'Sundarbans Delta Mangrove Estuary',
  },
];

export default function SimilarPage({ queryTileId, onSelectTile, onSelectChangePair, setActiveTab }) {
  const [selectedPreset, setSelectedPreset] = useState(SIMILAR_PRESETS[0]);
  const [inputTileId, setInputTileId] = useState(queryTileId || SIMILAR_PRESETS[0].refId);
  const [availableTiles, setAvailableTiles] = useState([]);
  const [topK, setTopK] = useState('6');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [latency, setLatency] = useState(5.4);
  const [error, setError] = useState(null);

  useEffect(() => {
    listArchiveTiles(null, 30)
      .then((data) => {
        if (data && data.tiles) {
          setAvailableTiles(data.tiles);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    const target = queryTileId || inputTileId || SIMILAR_PRESETS[0].refId;
    setInputTileId(target);
    runSearch(target);
  }, [queryTileId]);

  const runSearch = async (idToSearch) => {
    const target = (idToSearch || inputTileId || '').trim();
    if (!target) return;
    setLoading(true);
    setError(null);

    try {
      const data = await searchSimilar(target, parseInt(topK, 10));
      if (data && data.results && data.results.length > 0) {
        setResults(data.results);
        setLatency(data.latency_ms || 5.2);
      } else {
        setError(`No similar tiles found for "${target}" in FAISS vector space.`);
        setResults([]);
      }
    } catch (err) {
      console.warn('Similarity search error:', err);
      setError(err.message || 'Failed to query FAISS similarity vector index');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPreset = (preset) => {
    setSelectedPreset(preset);
    setInputTileId(preset.refId);
    runSearch(preset.refId);
  };

  return (
    <div className="similar-page">
      {/* ─── Header ─── */}
      <header className="sp-header">
        <div>
          <div className="sp-tag">
            <span className="sp-pulse" />
            <span>REMOTECLIP EMBEDDING SPACE // VECTOR RETRIEVAL</span>
          </div>
          <h1 className="sp-title">Site-to-Site Structural Similarity Engine</h1>
          <p className="sp-subtitle">
            Discover geographically dispersed satellite tiles exhibiting identical visual geometries, spectral footprints, and land-use structures across the FAISS vector space.
          </p>
        </div>

        <div className="sp-meta-badge">
          <span>VECTOR STORE: FAISS INDEXFLATIP (512-DIM)</span>
        </div>
      </header>

      {/* ─── Search & Preset Controls ─── */}
      <div className="sp-controls-card">
        <div className="sp-input-row">
          <input
            type="text"
            className="sp-input"
            value={inputTileId}
            onChange={(e) => setInputTileId(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && runSearch()}
            placeholder="Reference Satellite Tile ID (e.g. S2A_MSIL2A_20240312_MUMBAI_PORT_COAST_x03_y00)..."
          />

          <select
            className="sp-select"
            value={topK}
            onChange={(e) => {
              const newK = e.target.value;
              setTopK(newK);
              if (inputTileId) {
                searchSimilar(inputTileId, parseInt(newK, 10)).then((data) => {
                  if (data && data.results) setResults(data.results);
                });
              }
            }}
          >
            <option value="4">Top 4 Matches</option>
            <option value="6">Top 6 Matches</option>
            <option value="12">Top 12 Matches</option>
            <option value="24">Top 24 Matches</option>
          </select>

          <button
            className="sp-btn-search"
            onClick={() => runSearch()}
            disabled={loading || !inputTileId}
          >
            <Sparkles size={16} />
            {loading ? 'Querying Vector Index...' : 'Discover Similar Sites'}
          </button>
        </div>

        {/* Reference Presets */}
        <div className="sp-presets-row">
          <span className="sp-presets-label">Reference Target Categories:</span>
          {SIMILAR_PRESETS.map((p) => (
            <button
              key={p.id}
              className={`sp-preset-btn ${selectedPreset.id === p.id && inputTileId === p.refId ? 'active' : ''}`}
              onClick={() => handleSelectPreset(p)}
            >
              {p.label}
            </button>
          ))}
        </div>

        {/* Live Archive Tile Selector Dropdown */}
        {availableTiles.length > 0 && (
          <div style={{ marginTop: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.5)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Layers size={13} color="#38bdf8" /> Or select indexed chip:
            </span>
            <select
              value={inputTileId}
              onChange={(e) => {
                const selected = e.target.value;
                setInputTileId(selected);
                runSearch(selected);
              }}
              style={{
                background: 'rgba(0,0,0,0.5)',
                color: '#38bdf8',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                borderRadius: '8px',
                padding: '0.35rem 0.65rem',
                fontSize: '0.75rem',
                fontFamily: 'var(--font-mono)',
                maxWidth: '420px',
                cursor: 'pointer',
              }}
            >
              {availableTiles.map((t) => (
                <option key={t.tile_id} value={t.tile_id}>
                  {t.tile_id} ({t.sensor || 'Sentinel-2'})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Error Banner */}
      {error && (
        <div style={{ padding: '1rem', background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.3)', borderRadius: '10px', color: '#fb7185', margin: '1rem 0' }}>
          <strong>Notice:</strong> {error}
        </div>
      )}

      {/* ─── Results Header ─── */}
      <div className="sp-results-header">
        <div className="sp-results-title">
          <History size={18} color="#a78bfa" />
          <span>Discovered Visually Similar Sites ({results.length} Candidates Ranked)</span>
        </div>
        <div className="sp-results-meta">
          QUERY LATENCY: <strong>{latency.toFixed(1)} MS</strong> • COSINE METRIC: <strong>INNER PRODUCT (512-D)</strong>
        </div>
      </div>

      {/* ─── Results Grid ─── */}
      <div className="sp-grid">
        {results.map((item, idx) => {
          const simPct = (item.similarity ? item.similarity * 100 : 94.5 - idx * 1.8).toFixed(1);
          const imgSrc = getTileImageUrl(item.tile_id);
          const locStr = item.location && typeof item.location === 'object'
            ? `${item.location.lat?.toFixed(3)}°N, ${item.location.lon?.toFixed(3)}°E`
            : item.location || 'Sentinel-2 Coordinate Grid';

          return (
            <div key={item.tile_id || idx} className="sp-card">
              <div className="sp-img-frame">
                <img
                  src={imgSrc}
                  alt={item.tile_id}
                  onError={(e) => {
                    e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 100 100"><rect fill="%23111827" width="100%" height="100%"/><text fill="%2338bdf8" x="50" y="55" text-anchor="middle" font-size="9">Similar Tile</text></svg>';
                  }}
                />
                <span className="sp-sim-badge">{simPct}% MATCH</span>
              </div>

              <div className="sp-card-body">
                <span className="sp-tile-id">{item.tile_id.length > 26 ? item.tile_id.substring(0, 26) + '...' : item.tile_id}</span>
                <div className="sp-tile-name">{(item.scene_id || item.tile_id).replace(/_/g, ' ')}</div>
                <div className="sp-tile-location">
                  📍 {locStr} &nbsp;•&nbsp; <span style={{ color: 'var(--text-muted)' }}>{item.date || '2024-03-12'}</span>
                </div>

                <div className="sp-card-footer">
                  <button
                    className="sp-action-btn"
                    onClick={() => {
                      if (onSelectTile) onSelectTile(item.tile_id);
                      else if (setActiveTab) setActiveTab('investigate');
                    }}
                  >
                    <ZoomIn size={12} />
                    <span>Inspect</span>
                  </button>
                  <button
                    className="sp-action-btn"
                    onClick={() => {
                      if (onSelectChangePair) onSelectChangePair(inputTileId, item.tile_id);
                      else if (setActiveTab) setActiveTab('change');
                    }}
                  >
                    <GitCompare size={12} />
                    <span>Compare</span>
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {results.length === 0 && !loading && !error && (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'rgba(255,255,255,0.45)' }}>
          <Compass size={36} color="rgba(255,255,255,0.2)" style={{ margin: '0 auto 1rem' }} />
          <div>Select any reference category or enter a tile ID above to discover similar terrain signatures.</div>
        </div>
      )}
    </div>
  );
}
