import React, { useState, useEffect } from 'react';
import { ZoomIn, MapPin, Activity, Shield, Sparkles, GitCompare, History, Calendar, Layers } from 'lucide-react';
import { getTileDetails, getTileImageUrl } from '../api/client';
import './InvestigationPage.css';

const PRESET_TILES = [
  {
    tile_id: 'DELHI_S2_20260115_T1_x01_y01',
    name: 'Delhi-NCR Infrastructure Hub',
    region: 'National Capital Region, India',
    date: '2026-01-15',
    center_lat: 28.6139,
    center_lon: 77.2090,
    bbox: '28.58°N, 77.16°E to 28.64°N, 77.25°E',
    cloud_cover: '0.12%',
    gsd: '10m GSD',
    bands: { blue: 62, green: 78, red: 85, nir: 44 },
    provenance_id: 'PROV-DELHI-001',
    image: 'https://images.unsplash.com/photo-1524661135-423995f22d0b?auto=format&fit=crop&w=1280&q=85',
  },
  {
    tile_id: 'MUMBAI_S2_20260210_PORT_x02_y01',
    name: 'Mumbai Jawaharlal Nehru Port',
    region: 'Navi Mumbai Coastline, Maharashtra',
    date: '2026-02-10',
    center_lat: 18.9499,
    center_lon: 72.9515,
    bbox: '18.91°N, 72.91°E to 18.98°N, 72.99°E',
    cloud_cover: '0.04%',
    gsd: '10m GSD',
    bands: { blue: 85, green: 72, red: 54, nir: 28 },
    provenance_id: 'PROV-MUMBAI-002',
    image: 'https://images.unsplash.com/photo-1508873696983-2df57046475b?auto=format&fit=crop&w=1280&q=85',
  },
  {
    tile_id: 'SUNDARBANS_S2_20260301_DELTA_x01_y03',
    name: 'Sundarbans Mangrove Estuary',
    region: 'Sundarbans Biosphere, West Bengal',
    date: '2026-03-01',
    center_lat: 21.9497,
    center_lon: 88.9007,
    bbox: '21.91°N, 88.85°E to 21.98°N, 88.95°E',
    cloud_cover: '0.35%',
    gsd: '10m GSD',
    bands: { blue: 45, green: 65, red: 52, nir: 92 },
    provenance_id: 'PROV-SUNDAR-003',
    image: 'https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=1280&q=85',
  },
  {
    tile_id: 'BANGALORE_S2_20260220_TECH_x03_y02',
    name: 'Bangalore Electronic City Grid',
    region: 'South Bangalore, Karnataka',
    date: '2026-02-20',
    center_lat: 12.8452,
    center_lon: 77.6602,
    bbox: '12.81°N, 77.62°E to 12.88°N, 77.70°E',
    cloud_cover: '0.08%',
    gsd: '10m GSD',
    bands: { blue: 68, green: 74, red: 79, nir: 58 },
    provenance_id: 'PROV-BLR-004',
    image: 'https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=1280&q=85',
  },
];

export default function InvestigationPage({ tileId, onSelectChangePair, onFindSimilar, onSelectProvenance, setActiveTab }) {
  const [currentTile, setCurrentTile] = useState(null);
  const [bandMode, setBandMode] = useState('rgb'); // 'rgb', 'cir', 'ndvi', 'ndwi'

  useEffect(() => {
    if (tileId) {
      // Find preset or load details
      const found = PRESET_TILES.find(t => t.tile_id === tileId);
      if (found) {
        setCurrentTile(found);
      } else {
        // Fallback / API query
        getTileDetails(tileId)
          .then(data => {
            setCurrentTile({
              ...PRESET_TILES[0],
              ...data,
              tile_id: tileId,
              name: `Observation Chip ${tileId}`,
            });
          })
          .catch(() => {
            setCurrentTile({
              ...PRESET_TILES[0],
              tile_id: tileId,
              name: `Chip: ${tileId}`,
            });
          });
      }
    } else {
      // Default to first preset if no tile passed
      setCurrentTile(PRESET_TILES[0]);
    }
  }, [tileId]);

  if (!currentTile) {
    return <div className="inspector-page" style={{ textAlign: 'center', padding: '4rem' }}>Loading tile telemetry...</div>;
  }

  const bandConfig = {
    rgb: { label: 'True Color (RGB)', desc: 'Natural color composite (B4, B3, B2)' },
    cir: { label: 'Color Infrared (CIR)', desc: 'False-color vegetation reflectance (B8, B4, B3)' },
    ndvi: { label: 'NDVI Index', desc: 'Normalized Difference Vegetation Index' },
    ndwi: { label: 'NDWI Moisture', desc: 'Normalized Difference Water & Moisture' },
  };

  return (
    <div className="inspector-page">
      {/* ─── Header ─── */}
      <header className="ip-header">
        <div>
          <div className="ip-tag">
            <span className="ip-pulse" />
            <span>GEONEXA SATELLITE TILE INSPECTOR // 256×256 CHIP</span>
          </div>
          <h1 className="ip-title">{currentTile.name}</h1>
          <p className="ip-subtitle">
            Inspect radiometric spectral channels, ground coordinates, and multi-band reflectance profiles for chip <code>{currentTile.tile_id}</code>.
          </p>
        </div>

        <div className="ip-top-actions">
          <button
            className="ip-btn-action"
            onClick={() => onFindSimilar && onFindSimilar(currentTile.tile_id)}
          >
            <Sparkles size={14} color="#38bdf8" />
            Find Similar Sites
          </button>
          <button
            className="ip-btn-action ip-btn-primary"
            onClick={() => onSelectChangePair && onSelectChangePair(currentTile.tile_id, null)}
          >
            <GitCompare size={14} color="#34d399" />
            Change Analysis
          </button>
          <button
            className="ip-btn-action"
            onClick={() => onSelectProvenance && onSelectProvenance(currentTile.provenance_id)}
          >
            <Shield size={14} color="#a78bfa" />
            Provenance
          </button>
        </div>
      </header>

      {/* ─── Main Stage: Visual Preview + Spectral & Metadata Panels ─── */}
      <div className="ip-stage">
        {/* Left: Visual Preview Frame */}
        <div className="ip-viewer-card">
          <div className="ip-viewer-bar">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <ZoomIn size={16} color="#38bdf8" />
              <span style={{ fontSize: '0.82rem', fontWeight: 700, fontFamily: 'Chakra Petch' }}>
                SPECTRAL CHANNEL: {bandConfig[bandMode].label.toUpperCase()}
              </span>
            </div>

            <div className="ip-band-tabs">
              <button
                className={`ip-band-btn ${bandMode === 'rgb' ? 'active' : ''}`}
                onClick={() => setBandMode('rgb')}
              >
                True Color
              </button>
              <button
                className={`ip-band-btn ${bandMode === 'cir' ? 'active' : ''}`}
                onClick={() => setBandMode('cir')}
              >
                Color Infrared (CIR)
              </button>
              <button
                className={`ip-band-btn ${bandMode === 'ndvi' ? 'active' : ''}`}
                onClick={() => setBandMode('ndvi')}
              >
                NDVI Index
              </button>
              <button
                className={`ip-band-btn ${bandMode === 'ndwi' ? 'active' : ''}`}
                onClick={() => setBandMode('ndwi')}
              >
                NDWI Water
              </button>
            </div>
          </div>

          <div className={`ip-canvas-frame mode-${bandMode}`}>
            <img src={currentTile.image} alt={currentTile.name} />

            <div className="ip-hud">
              <div>CENTER: <strong>{currentTile.center_lat?.toFixed(4)}°N, {currentTile.center_lon?.toFixed(4)}°E</strong></div>
              <div>GSD: <strong>{currentTile.gsd}</strong></div>
              <div>ACQUIRED: <strong>{currentTile.date}</strong></div>
            </div>
          </div>
        </div>

        {/* Right: Metadata & Spectral Breakdown */}
        <div className="ip-info-col">
          {/* Geospatial Metadata Card */}
          <div className="ip-card">
            <div className="ip-card-title">
              <MapPin size={16} />
              Geospatial & Acquisition Parameters
            </div>

            <div className="ip-meta-grid">
              <div className="ip-meta-cell">
                <div className="ip-meta-lbl">Geographic Region</div>
                <div className="ip-meta-val" style={{ fontSize: '0.8rem', color: '#38bdf8' }}>{currentTile.region}</div>
              </div>
              <div className="ip-meta-cell">
                <div className="ip-meta-lbl">Bounding Box (BBOX)</div>
                <div className="ip-meta-val" style={{ fontSize: '0.75rem' }}>{currentTile.bbox}</div>
              </div>
              <div className="ip-meta-cell">
                <div className="ip-meta-lbl">Cloud Cover</div>
                <div className="ip-meta-val" style={{ color: '#34d399' }}>{currentTile.cloud_cover}</div>
              </div>
              <div className="ip-meta-cell">
                <div className="ip-meta-lbl">Chip Dimension</div>
                <div className="ip-meta-val">256 × 256 px</div>
              </div>
            </div>
          </div>

          {/* Spectral Reflectance Profile Card */}
          <div className="ip-card">
            <div className="ip-card-title">
              <Activity size={16} />
              Radiometric Reflectance Profile (DNs)
            </div>

            <div className="ip-spectral-bars">
              <div className="ip-spec-row">
                <div className="ip-spec-header">
                  <span>Band 2 (Blue · 490nm)</span>
                  <strong>{currentTile.bands.blue}%</strong>
                </div>
                <div className="ip-bar-track">
                  <div className="ip-bar-fill" style={{ width: `${currentTile.bands.blue}%`, background: '#38bdf8' }} />
                </div>
              </div>

              <div className="ip-spec-row">
                <div className="ip-spec-header">
                  <span>Band 3 (Green · 560nm)</span>
                  <strong>{currentTile.bands.green}%</strong>
                </div>
                <div className="ip-bar-track">
                  <div className="ip-bar-fill" style={{ width: `${currentTile.bands.green}%`, background: '#34d399' }} />
                </div>
              </div>

              <div className="ip-spec-row">
                <div className="ip-spec-header">
                  <span>Band 4 (Red · 665nm)</span>
                  <strong>{currentTile.bands.red}%</strong>
                </div>
                <div className="ip-bar-track">
                  <div className="ip-bar-fill" style={{ width: `${currentTile.bands.red}%`, background: '#f43f5e' }} />
                </div>
              </div>

              <div className="ip-spec-row">
                <div className="ip-spec-header">
                  <span>Band 8 (Near-Infrared · 842nm)</span>
                  <strong>{currentTile.bands.nir}%</strong>
                </div>
                <div className="ip-bar-track">
                  <div className="ip-bar-fill" style={{ width: `${currentTile.bands.nir}%`, background: '#a78bfa' }} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ─── Chip Presets Gallery ─── */}
      <section className="ip-presets">
        <div className="ip-presets-heading">Featured Satellite Imagery Chips across India ({PRESET_TILES.length} Regions)</div>
        <div className="ip-presets-grid">
          {PRESET_TILES.map((pt) => (
            <div
              key={pt.tile_id}
              className={`ip-preset-card ${currentTile.tile_id === pt.tile_id ? 'active' : ''}`}
              onClick={() => setCurrentTile(pt)}
            >
              <div className="ip-pr-title">{pt.name}</div>
              <div className="ip-pr-desc">{pt.region}</div>
              <div className="ip-pr-meta">
                <span>{pt.date}</span>
                <span>{pt.cloud_cover} CLOUD</span>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
