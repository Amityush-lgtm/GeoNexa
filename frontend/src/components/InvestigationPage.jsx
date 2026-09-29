import React, { useState, useEffect } from 'react';
import { Compass, Calendar, MapPin, Layers, ArrowRight, ShieldCheck, RefreshCw, ZoomIn } from 'lucide-react';
import { getTileDetails, getTemporalObservations, getTileImageUrl } from '../api/client';

export default function InvestigationPage({ tileId, onSelectChangePair, onFindSimilar, onSelectProvenance, setActiveTab }) {
  const [tile, setTile] = useState(null);
  const [temporal, setTemporal] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedCompareTileId, setSelectedCompareTileId] = useState(null);

  useEffect(() => {
    if (!tileId) return;
    loadData(tileId);
  }, [tileId]);

  const loadData = async (id) => {
    setLoading(true);
    setError(null);
    try {
      const [tileData, temporalData] = await Promise.all([
        getTileDetails(id),
        getTemporalObservations(id).catch(() => ({ observations: [] })),
      ]);
      setTile(tileData);
      setTemporal(temporalData.observations || []);
      if (temporalData.observations?.length > 1) {
        // Default comparison to another observation
        const other = temporalData.observations.find((o) => o.tile_id !== id);
        if (other) setSelectedCompareTileId(other.tile_id);
      }
    } catch (err) {
      setError(err.message || 'Failed to load tile metadata');
    } finally {
      setLoading(false);
    }
  };

  if (!tileId) {
    return (
      <div className="container glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
        <Compass size={40} color="var(--accent-sky)" style={{ margin: '0 auto 1rem' }} />
        <h3 style={{ fontSize: '1.2rem', marginBottom: '0.5rem' }}>No Tile Selected for Inspection</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
          Select a satellite imagery chip from the Semantic Search results to inspect spectral attributes and temporal stacks.
        </p>
        <button className="btn btn-primary" onClick={() => setActiveTab('search')}>
          Go to Search
        </button>
      </div>
    );
  }

  return (
    <div className="container" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Top Header */}
      <div className="glass-panel-elevated" style={{ padding: '1.25rem 1.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span className="badge badge-cyan">INSPECTION ACTIVE</span>
            <h2 style={{ fontSize: '1.2rem', fontFamily: 'var(--font-mono)' }}>{tileId}</h2>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Geospatial Chip Resolution: 256×256 px | Multi-Band Georeferenced Extent
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-secondary btn-sm" onClick={() => onFindSimilar(tileId)}>
            Find Similar Sites
          </button>
        </div>
      </div>

      {loading && <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>Loading tile geospatial assets...</div>}
      {error && <div style={{ padding: '1rem', background: 'rgba(244,63,94,0.15)', color: '#fb7185', borderRadius: '8px' }}>{error}</div>}

      {tile && (
        <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: '1.5rem' }}>
          {/* Visual Preview Frame */}
          <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ZoomIn size={16} color="var(--accent-sky)" />
              High-Resolution Chip Imagery
            </h3>
            <div className="imagery-frame" style={{ height: '380px', borderRadius: '12px' }}>
              <img src={getTileImageUrl(tileId)} alt={tileId} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              <span>Bands: R, G, B, NIR (True Color View)</span>
              <span>Coordinates: {tile.center_lat?.toFixed(4)}°N, {tile.center_lon?.toFixed(4)}°E</span>
            </div>
          </div>

          {/* Metadata & Coordinate Inspector */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div className="glass-panel" style={{ padding: '1.5rem' }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <MapPin size={16} color="var(--accent-emerald)" />
                Geospatial & Acquisition Metadata
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.85rem', fontSize: '0.8rem' }}>
                <div>
                  <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>Source Scene</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{tile.scene_id}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>Acquisition Date</div>
                  <div style={{ fontWeight: 600 }}>{tile.acquisition_date || '2026-01-15'}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>Sensor Instrument</div>
                  <div>{tile.sensor || 'Sentinel-2 (MSI)'}</div>
                </div>
                <div>
                  <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>CRS / Projection</div>
                  <div style={{ fontFamily: 'var(--font-mono)' }}>{tile.crs || 'EPSG:4326'}</div>
                </div>
                <div style={{ gridColumn: 'span 2' }}>
                  <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>Bounding Box (MinX, MinY, MaxX, MaxY)</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', background: 'rgba(0,0,0,0.3)', padding: '0.35rem 0.5rem', borderRadius: '4px', marginTop: '0.2rem' }}>
                    [{tile.bounds_minx?.toFixed(4)}, {tile.bounds_miny?.toFixed(4)}, {tile.bounds_maxx?.toFixed(4)}, {tile.bounds_maxy?.toFixed(4)}]
                  </div>
                </div>
              </div>
            </div>

            {/* Temporal Stack Timeline */}
            <div className="glass-panel" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Calendar size={16} color="var(--accent-amber)" />
                  Temporal Observation Stack ({temporal.length})
                </h3>
              </div>

              {temporal.length <= 1 ? (
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Single observation in archive. Ingest multi-temporal scenes to unlock temporal change analysis.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                  {temporal.map((obs) => {
                    const isSelf = obs.tile_id === tileId;
                    const isSelected = obs.tile_id === selectedCompareTileId;

                    return (
                      <div
                        key={obs.tile_id}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '0.6rem 0.85rem',
                          background: isSelected ? 'rgba(56, 189, 248, 0.12)' : 'rgba(0,0,0,0.25)',
                          border: isSelected ? '1px solid rgba(56, 189, 248, 0.4)' : '1px solid var(--border-subtle)',
                          borderRadius: '8px',
                          cursor: isSelf ? 'default' : 'pointer'
                        }}
                        onClick={() => !isSelf && setSelectedCompareTileId(obs.tile_id)}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                          <img
                            src={getTileImageUrl(obs.tile_id)}
                            alt=""
                            style={{ width: '38px', height: '38px', borderRadius: '4px', objectFit: 'cover' }}
                          />
                          <div>
                            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: isSelf ? '#38bdf8' : '#ffffff' }}>
                              {obs.acquisition_date} {isSelf && '(Current)'}
                            </div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                              {obs.tile_id}
                            </div>
                          </div>
                        </div>

                        {!isSelf && (
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              onSelectChangePair(tileId, obs.tile_id);
                              setActiveTab('change');
                            }}
                          >
                            Analyze Change
                            <ArrowRight size={13} />
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
