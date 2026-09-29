import React, { useState, useEffect } from 'react';
import { GitCompare, CheckCircle2, XCircle, HelpCircle, Layers, Sliders, Shield, AlertTriangle, ArrowRight } from 'lucide-react';
import { analyzeChange, submitReview, getTileImageUrl } from '../api/client';
import ConfidenceBreakdown from './ConfidenceBreakdown';

export default function ChangePage({ t1TileId, t2TileId, onSelectProvenance, setActiveTab }) {
  const [t1, setT1] = useState(t1TileId || '');
  const [t2, setT2] = useState(t2TileId || '');
  const [threshold, setThreshold] = useState(0.25);
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);

  // Mask Overlay Controls
  const [showMask, setShowMask] = useState(true);
  const [maskOpacity, setMaskOpacity] = useState(0.65);

  // Review Feedback
  const [decision, setDecision] = useState(null);
  const [analystNotes, setAnalystNotes] = useState('');
  const [reviewSubmitted, setReviewSubmitted] = useState(false);

  useEffect(() => {
    if (t1TileId) setT1(t1TileId);
    if (t2TileId) setT2(t2TileId);
    if (t1TileId && t2TileId) {
      handleAnalyze(t1TileId, t2TileId);
    }
  }, [t1TileId, t2TileId]);

  const handleAnalyze = async (overrideT1, overrideT2) => {
    const id1 = overrideT1 || t1;
    const id2 = overrideT2 || t2;
    if (!id1 || !id2) return;

    setLoading(true);
    setError(null);
    setReviewSubmitted(false);
    setDecision(null);

    try {
      const data = await analyzeChange({
        t1_tile_id: id1,
        t2_tile_id: id2,
        threshold: parseFloat(threshold),
        min_area_pixels: 20,
      });
      setAnalysis(data);
    } catch (err) {
      setError(err.message || 'Change detection failed');
    } finally {
      setLoading(false);
    }
  };

  const handleReviewSubmit = async (dec) => {
    if (!analysis) return;
    try {
      await submitReview({
        analysis_id: analysis.analysis_id,
        tile_id: t2,
        decision: dec,
        notes: analystNotes,
        analyst: 'Analyst_Alpha',
      });
      setDecision(dec);
      setReviewSubmitted(true);
    } catch (err) {
      alert('Failed to submit analyst review: ' + err.message);
    }
  };

  return (
    <div className="container" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header & Controls Bar */}
      <div className="glass-panel-elevated" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ fontSize: '1.3rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <GitCompare size={22} color="var(--accent-cyan)" />
              Multi-Temporal Change Analysis Engine
            </h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Deterministic change segmentation with radiometric calibration, false-alarm suppression & confidence modeling.
            </p>
          </div>
          {analysis && (
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                className="btn btn-outline btn-sm"
                onClick={() => onSelectProvenance(analysis.provenance_id)}
              >
                <Shield size={14} />
                Trace Provenance
              </button>
            </div>
          )}
        </div>

        {/* Inputs */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 180px auto', gap: '0.75rem', alignItems: 'end' }}>
          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>T1 Baseline Tile ID</label>
            <input
              type="text"
              value={t1}
              onChange={(e) => setT1(e.target.value)}
              placeholder="e.g. DELHI_S2_20260115_T1_x01_y01"
              style={{ width: '100%', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '0.45rem 0.65rem', color: '#ffffff', fontSize: '0.8rem', fontFamily: 'var(--font-mono)' }}
            />
          </div>
          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>T2 Target Tile ID</label>
            <input
              type="text"
              value={t2}
              onChange={(e) => setT2(e.target.value)}
              placeholder="e.g. DELHI_S2_20260320_T2_x01_y01"
              style={{ width: '100%', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '0.45rem 0.65rem', color: '#ffffff', fontSize: '0.8rem', fontFamily: 'var(--font-mono)' }}
            />
          </div>
          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem' }}>Diff Threshold ({threshold})</label>
            <input
              type="range"
              min="0.1"
              max="0.6"
              step="0.05"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              style={{ width: '100%' }}
            />
          </div>
          <button
            className="btn btn-primary"
            onClick={() => handleAnalyze()}
            disabled={loading || !t1 || !t2}
          >
            {loading ? 'Processing...' : 'Run Analysis'}
          </button>
        </div>
      </div>

      {error && <div style={{ padding: '1rem', background: 'rgba(244,63,94,0.15)', color: '#fb7185', borderRadius: '8px' }}>{error}</div>}

      {/* Main Analysis Display */}
      {analysis && (
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '1.5rem' }}>
          {/* Visual Comparison Triple View */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              {/* T1 Observation */}
              <div className="glass-panel" style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                  <span style={{ fontWeight: 700, color: 'var(--accent-sky)' }}>T1 (Baseline)</span>
                  <span style={{ color: 'var(--text-muted)' }}>{analysis.t1_date || '2026-01-15'}</span>
                </div>
                <div className="imagery-frame" style={{ height: '240px' }}>
                  <img src={getTileImageUrl(t1)} alt="T1" />
                </div>
              </div>

              {/* T2 Observation */}
              <div className="glass-panel" style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                  <span style={{ fontWeight: 700, color: '#34d399' }}>T2 (Target)</span>
                  <span style={{ color: 'var(--text-muted)' }}>{analysis.t2_date || '2026-03-20'}</span>
                </div>
                <div className="imagery-frame" style={{ height: '240px', position: 'relative' }}>
                  <img src={getTileImageUrl(t2)} alt="T2" />
                  {/* Change Mask Overlay */}
                  {showMask && (
                    <div
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
                        height: '100%',
                        background: 'radial-gradient(circle at 50% 50%, rgba(244, 63, 94, 0.45) 0%, transparent 70%)',
                        mixBlendMode: 'screen',
                        opacity: maskOpacity,
                        pointerEvents: 'none',
                        border: '2px dashed #f43f5e',
                      }}
                    />
                  )}
                </div>
              </div>
            </div>

            {/* Overlay Controls */}
            <div className="glass-panel" style={{ padding: '0.75rem 1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={showMask}
                  onChange={(e) => setShowMask(e.target.checked)}
                />
                <span>Overlay Detected Change Mask</span>
              </label>

              {showMask && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Mask Opacity:</span>
                  <input
                    type="range"
                    min="0.2"
                    max="1.0"
                    step="0.05"
                    value={maskOpacity}
                    onChange={(e) => setMaskOpacity(parseFloat(e.target.value))}
                    style={{ width: '100px' }}
                  />
                </div>
              )}
            </div>

            {/* Earliest Supported Observation Timeline Card */}
            {analysis.earliest_supported_observation && (
              <div className="glass-panel" style={{ padding: '1rem', background: 'rgba(6, 182, 212, 0.08)', border: '1px solid rgba(6, 182, 212, 0.3)' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#38bdf8', marginBottom: '0.2rem' }}>
                  Earliest Supported Observation in Indexed Archive
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-main)' }}>
                  {analysis.earliest_supported_observation}
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Confidence Breakdown & Analyst Decision */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <ConfidenceBreakdown details={analysis.confidence_details} score={analysis.confidence} />

            {/* Change Classification Card */}
            <div className="glass-panel" style={{ padding: '1.25rem' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Detected Classification
              </div>
              <div style={{ fontSize: '1.2rem', fontWeight: 800, color: analysis.change_type.includes('NO_CHANGE') ? '#34d399' : '#fb7185', marginTop: '0.25rem' }}>
                {analysis.change_type.replace(/_/g, ' ')}
              </div>
            </div>

            {/* Analyst Review Box */}
            <div className="glass-panel-elevated" style={{ padding: '1.25rem' }}>
              <h4 style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.75rem' }}>
                Analyst Verification & Decision
              </h4>

              {reviewSubmitted ? (
                <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '8px', padding: '0.75rem', color: '#34d399', fontSize: '0.8rem' }}>
                  ✓ Decision <strong>{decision?.toUpperCase()}</strong> logged to audit provenance.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <textarea
                    rows={2}
                    value={analystNotes}
                    onChange={(e) => setAnalystNotes(e.target.value)}
                    placeholder="Enter analyst notes or justification..."
                    style={{ width: '100%', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-subtle)', borderRadius: '6px', padding: '0.5rem', color: '#ffffff', fontSize: '0.8rem', resize: 'none' }}
                  />
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem' }}>
                    <button
                      className="btn btn-sm"
                      style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', border: '1px solid rgba(16, 185, 129, 0.4)' }}
                      onClick={() => handleReviewSubmit('confirmed')}
                    >
                      <CheckCircle2 size={14} />
                      Confirm
                    </button>
                    <button
                      className="btn btn-sm"
                      style={{ background: 'rgba(244, 63, 94, 0.2)', color: '#fb7185', border: '1px solid rgba(244, 63, 94, 0.4)' }}
                      onClick={() => handleReviewSubmit('rejected')}
                    >
                      <XCircle size={14} />
                      Reject
                    </button>
                    <button
                      className="btn btn-sm"
                      style={{ background: 'rgba(245, 158, 11, 0.2)', color: '#fbbf24', border: '1px solid rgba(245, 158, 11, 0.4)' }}
                      onClick={() => handleReviewSubmit('uncertain')}
                    >
                      <HelpCircle size={14} />
                      Uncertain
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
