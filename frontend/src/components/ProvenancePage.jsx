import React, { useState, useEffect } from 'react';
import { ShieldCheck, Search, FileCode, CheckCircle, Clock, Cpu, GitCommit, Layers, ArrowRight } from 'lucide-react';
import { getProvenanceRecord, listRecentProvenance } from '../api/client';

export default function ProvenancePage({ initialProvenanceId }) {
  const [provenanceId, setProvenanceId] = useState(initialProvenanceId || '');
  const [record, setRecord] = useState(null);
  const [recentRecords, setRecentRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    listRecentProvenance(12)
      .then((data) => {
        if (Array.isArray(data)) setRecentRecords(data);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (initialProvenanceId) {
      setProvenanceId(initialProvenanceId);
      handleFetch(initialProvenanceId);
    }
  }, [initialProvenanceId]);

  const handleFetch = async (overrideId) => {
    const id = overrideId || provenanceId;
    if (!id) return;

    setLoading(true);
    setError(null);

    try {
      const data = await getProvenanceRecord(id);
      setRecord(data);
    } catch (err) {
      setError(err.message || 'Provenance record not found');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', padding: '1.5rem 0' }}>
      {/* Header */}
      <div className="glass-panel-elevated" style={{ padding: '1.5rem 2rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <ShieldCheck size={22} color="#34d399" />
            Audit Provenance & Decision Traceability Inspector
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
            Every search result, similarity match, and multi-temporal change mask is immutably cryptographically traceable back to source imagery, model version, and inference parameters.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <input
            type="text"
            value={provenanceId}
            onChange={(e) => setProvenanceId(e.target.value)}
            placeholder="Enter Provenance ID (e.g. prov-6170d744f4334311)..."
            style={{ flex: 1, background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '0.55rem 0.85rem', color: '#ffffff', fontSize: '0.85rem', fontFamily: 'var(--font-mono)' }}
          />
          <button
            className="btn btn-primary"
            onClick={() => handleFetch()}
            disabled={loading || !provenanceId}
          >
            {loading ? 'Fetching...' : 'Inspect Trace'}
          </button>
        </div>
      </div>

      {error && <div style={{ padding: '1rem', background: 'rgba(244,63,94,0.15)', color: '#fb7185', borderRadius: '8px' }}>{error}</div>}

      {/* Record View */}
      {record ? (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
          {/* Metadata Card */}
          <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <GitCommit size={16} color="var(--accent-sky)" />
              Execution Trace Context
            </h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.8rem' }}>
              <div style={{ background: 'rgba(0,0,0,0.25)', padding: '0.75rem', borderRadius: '8px' }}>
                <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>Provenance Record ID</div>
                <div style={{ fontFamily: 'var(--font-mono)', color: '#38bdf8', fontWeight: 700, marginTop: '0.2rem' }}>
                  {record.provenance_id}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div style={{ background: 'rgba(0,0,0,0.25)', padding: '0.75rem', borderRadius: '8px' }}>
                  <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>Operation Entity Type</div>
                  <div style={{ fontWeight: 600, textTransform: 'uppercase', color: '#34d399', marginTop: '0.2rem' }}>
                    {record.entity_type}
                  </div>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.25)', padding: '0.75rem', borderRadius: '8px' }}>
                  <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>Creation Timestamp</div>
                  <div style={{ marginTop: '0.2rem' }}>
                    {record.created_at}
                  </div>
                </div>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.25)', padding: '0.75rem', borderRadius: '8px' }}>
                <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>Embedding Model & Version</div>
                <div style={{ fontFamily: 'var(--font-mono)', marginTop: '0.2rem' }}>
                  {record.embedding_model || 'RemoteCLIP-ViT-B-32'} ({record.embedding_version || 'v2.1-finetuned'})
                </div>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.25)', padding: '0.75rem', borderRadius: '8px' }}>
                <div style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>System Processing Pipeline Version</div>
                <div style={{ fontFamily: 'var(--font-mono)', marginTop: '0.2rem' }}>
                  {record.processing_version || 'GeoNexa-Core-0.1.0-AirGapped'}
                </div>
              </div>
            </div>
          </div>

          {/* JSON Payload Inspection */}
          <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FileCode size={16} color="var(--accent-indigo)" />
              Audit Payload & Parameters
            </h3>

            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.4rem' }}>Parameters:</div>
              <pre style={{ background: '#070a10', padding: '0.75rem', borderRadius: '8px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: '#38bdf8', overflowX: 'auto', maxHeight: '160px' }}>
                {JSON.stringify(record.parameters, null, 2)}
              </pre>
            </div>

            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.4rem' }}>Result Summary:</div>
              <pre style={{ background: '#070a10', padding: '0.75rem', borderRadius: '8px', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: '#34d399', overflowX: 'auto', maxHeight: '160px' }}>
                {JSON.stringify(record.result_summary, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      ) : (
        /* Recent Provenance Ledger */
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Clock size={16} color="#38bdf8" />
            Recent Search & Inference Audit Trail ({recentRecords.length} Records)
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
            {recentRecords.map((r) => (
              <div
                key={r.provenance_id}
                onClick={() => {
                  setProvenanceId(r.provenance_id);
                  setRecord(r);
                }}
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '10px',
                  padding: '1rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#38bdf8';
                  e.currentTarget.style.background = 'rgba(56,189,248,0.08)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)';
                  e.currentTarget.style.background = 'rgba(255,255,255,0.03)';
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: '#38bdf8', fontWeight: 700 }}>
                    {r.provenance_id}
                  </span>
                  <span style={{ fontSize: '0.68rem', color: '#34d399', textTransform: 'uppercase', fontWeight: 700, background: 'rgba(52,211,153,0.12)', padding: '2px 6px', borderRadius: '4px' }}>
                    {r.entity_type || 'INFERENCE'}
                  </span>
                </div>
                <div style={{ fontSize: '0.72rem', color: 'rgba(255,255,255,0.6)', marginBottom: '0.5rem' }}>
                  {r.query_text ? `"${r.query_text}"` : r.query_tile_id || 'Direct Tile Pipeline'}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.68rem', color: 'var(--text-dim)', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '0.4rem' }}>
                  <span>{r.created_at ? r.created_at.substring(0, 19).replace('T', ' ') : '2026-04-18'}</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '2px', color: '#38bdf8' }}>
                    Inspect <ArrowRight size={10} />
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
