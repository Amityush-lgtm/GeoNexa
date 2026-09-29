import React from 'react';
import { CheckCircle, AlertTriangle, Cloud, Sun, Layers } from 'lucide-react';

export default function ConfidenceBreakdown({ details, score }) {
  if (!details) return null;

  const getScoreColor = (val) => {
    if (val >= 0.7) return '#10b981';
    if (val >= 0.4) return '#f59e0b';
    return '#f43f5e';
  };

  const metrics = [
    { label: 'Structural Magnitude', value: details.structural, icon: Layers, note: 'Raw pixel/feature shift' },
    { label: 'Spectral Confirmation', value: details.spectral_confirmation, icon: CheckCircle, note: details.spectral_description || 'Physical index confirmation' },
    { label: 'Seasonal Confounder Risk', value: details.seasonal_confound, icon: Sun, inverted: true, note: `DOY delta: ${details.doy_diff_days || 0} days` },
    { label: 'Cloud / Haze Contamination', value: details.cloud_contamination, icon: Cloud, inverted: true, note: 'Atmospheric QA interference' },
    { label: 'Registration Quality', value: details.registration_quality, icon: CheckCircle, note: `Shift: ${details.registration_shift_px || 0}px (sub-pixel)` },
    { label: 'Temporal Persistence', value: details.persistence, icon: AlertTriangle, note: 'Consistency across observations' },
  ];

  return (
    <div className="glass-panel" style={{ padding: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h4 style={{ fontSize: '0.9rem', color: 'var(--text-main)', fontWeight: 700 }}>
          Confidence & Confounder Breakdown
        </h4>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Calibrated Confidence:</span>
          <span style={{
            fontSize: '1rem',
            fontWeight: 800,
            color: getScoreColor(score),
            padding: '2px 8px',
            background: 'rgba(255,255,255,0.05)',
            borderRadius: '6px'
          }}>
            {(score * 100).toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Spectral Indices Chips */}
      {(details.delta_ndvi !== undefined || details.delta_ndwi !== undefined) && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem', marginBottom: '1rem' }}>
          <div style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.25)', padding: '0.4rem 0.6rem', borderRadius: '6px', textAlign: 'center' }}>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Δ NDVI</div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: details.delta_ndvi < -0.1 ? '#fb7185' : '#34d399', fontFamily: 'var(--font-mono)' }}>
              {details.delta_ndvi > 0 ? `+${details.delta_ndvi.toFixed(3)}` : details.delta_ndvi?.toFixed(3) || '0.000'}
            </div>
          </div>
          <div style={{ background: 'rgba(56, 189, 248, 0.1)', border: '1px solid rgba(56, 189, 248, 0.25)', padding: '0.4rem 0.6rem', borderRadius: '6px', textAlign: 'center' }}>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Δ NDWI</div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: details.delta_ndwi > 0.1 ? '#38bdf8' : 'var(--text-main)', fontFamily: 'var(--font-mono)' }}>
              {details.delta_ndwi > 0 ? `+${details.delta_ndwi.toFixed(3)}` : details.delta_ndwi?.toFixed(3) || '0.000'}
            </div>
          </div>
          <div style={{ background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.25)', padding: '0.4rem 0.6rem', borderRadius: '6px', textAlign: 'center' }}>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Δ NDBI</div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: details.delta_ndbi > 0.1 ? '#fbbf24' : 'var(--text-main)', fontFamily: 'var(--font-mono)' }}>
              {details.delta_ndbi > 0 ? `+${details.delta_ndbi.toFixed(3)}` : details.delta_ndbi?.toFixed(3) || '0.000'}
            </div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {metrics.map((m, idx) => {
          const Icon = m.icon;
          const pct = Math.min(100, Math.max(0, (m.value || 0) * 100));
          const isNegativeFactor = m.inverted && m.value > 0.3;
          const barColor = m.inverted ? (m.value > 0.3 ? '#f43f5e' : '#10b981') : (m.value > 0.6 ? '#10b981' : '#f59e0b');

          return (
            <div key={idx} style={{ background: 'rgba(0,0,0,0.2)', padding: '0.65rem 0.85rem', borderRadius: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.35rem' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-main)', fontWeight: 600 }}>
                  <Icon size={14} color={barColor} />
                  {m.label}
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', color: isNegativeFactor ? '#fb7185' : 'var(--text-muted)' }}>
                  {pct.toFixed(0)}%
                </span>
              </div>
              {/* Progress Bar */}
              <div style={{ height: '6px', background: 'rgba(255,255,255,0.08)', borderRadius: '3px', overflow: 'hidden' }}>
                <div
                  style={{
                    height: '100%',
                    width: `${pct}%`,
                    background: barColor,
                    transition: 'width 0.5s ease',
                    borderRadius: '3px'
                  }}
                />
              </div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
                {m.note}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
