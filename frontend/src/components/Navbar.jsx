import React from 'react';
import { LayoutDashboard, Search, Compass, GitCompare, History, Database, ShieldCheck, ArrowLeft } from 'lucide-react';

const navItems = [
  { id: 'overview',    label: 'Overview',          icon: LayoutDashboard },
  { id: 'search',      label: 'Semantic Search',   icon: Search },
  { id: 'investigate', label: 'Tile Inspector',     icon: Compass },
  { id: 'change',      label: 'Change Engine',      icon: GitCompare },
  { id: 'similar',     label: 'Site Similarity',    icon: History },
  { id: 'provenance',  label: 'Provenance Trace',   icon: ShieldCheck },
  { id: 'archive',     label: 'Archive Ops',        icon: Database },
];

export default function Navbar({ activeTab, setActiveTab, onBackToLanding }) {
  return (
    <header
      style={{
        position: 'sticky',
        top: '1rem',
        zIndex: 100,
        height: '64px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        margin: '0.75rem 1.5rem',
        padding: '0 1.25rem',
        background: 'rgba(6, 9, 18, 0.75)',
        backdropFilter: 'blur(20px) saturate(180%)',
        WebkitBackdropFilter: 'blur(20px) saturate(180%)',
        border: '1px solid rgba(255, 255, 255, 0.12)',
        borderRadius: '16px',
        boxShadow: '0 10px 30px rgba(0, 0, 0, 0.4)',
      }}
    >
      {/* Brand */}
      <div
        style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', cursor: 'pointer', flexShrink: 0 }}
        onClick={() => setActiveTab('overview')}
      >
        <svg width="24" height="24" viewBox="0 0 256 256" fill="#38bdf8" style={{ filter: 'drop-shadow(0 0 8px rgba(56, 189, 248, 0.5))' }}>
          <path d="M 256 256 L 128 256 L 0 128 L 128 128 Z M 256 128 L 128 128 L 0 0 L 128 0 Z" />
        </svg>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.45rem' }}>
          <span
            style={{
              fontSize: '1.25rem',
              color: '#ffffff',
              fontFamily: "'Inter', sans-serif",
              fontWeight: 800,
              letterSpacing: '-0.02em',
            }}
          >
            GeoNexa
          </span>
          <span
            style={{
              fontSize: '0.62rem',
              color: '#38bdf8',
              border: '1px solid rgba(56, 189, 248, 0.4)',
              background: 'rgba(56, 189, 248, 0.12)',
              borderRadius: '9999px',
              padding: '1px 6px',
              fontWeight: 700,
              letterSpacing: '0.04em',
            }}
          >
            SIH26227
          </span>
        </div>
      </div>

      {/* Floating Center Pill for Navigation */}
      <nav
        className="scrollbar-hide"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.25rem',
          background: 'rgba(255, 255, 255, 0.06)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '9999px',
          padding: '0.25rem 0.45rem',
          overflow: 'auto',
          maxWidth: '60vw',
        }}
      >
        {navItems.map(({ id, label, icon: Icon }) => {
          const active = activeTab === id;
          return (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.38rem 0.85rem',
                borderRadius: '9999px',
                border: 'none',
                background: active ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
                color: active ? '#38bdf8' : 'rgba(255, 255, 255, 0.75)',
                fontWeight: active ? 700 : 500,
                fontSize: '0.8rem',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'all 0.15s ease',
              }}
            >
              <Icon size={14} />
              <span>{label}</span>
            </button>
          );
        })}
      </nav>

      {/* Actions & Offline Readiness */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexShrink: 0 }}>
        {onBackToLanding && (
          <button
            onClick={onBackToLanding}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              padding: '0.38rem 0.75rem',
              borderRadius: '9999px',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              background: 'rgba(255, 255, 255, 0.05)',
              color: 'rgba(255, 255, 255, 0.8)',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <ArrowLeft size={13} />
            <span>Landing</span>
          </button>
        )}

        <div className="badge badge-emerald" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.35rem 0.75rem' }}>
          <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#34d399', display: 'inline-block' }} className="pulse-indicator" />
          <span style={{ fontSize: '0.72rem', fontWeight: 700 }}>OFFLINE ACTIVE</span>
        </div>
      </div>
    </header>
  );
}
