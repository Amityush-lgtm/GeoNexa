import React from 'react';
import { Search, Compass, GitCompare, History, Database, ShieldCheck, ArrowLeft } from 'lucide-react';

const navItems = [
  { id: 'search',      label: 'Semantic Search',  icon: Search },
  { id: 'investigate', label: 'Tile Inspector',    icon: Compass },
  { id: 'change',      label: 'Change Engine',     icon: GitCompare },
  { id: 'similar',     label: 'Site Similarity',   icon: History },
  { id: 'provenance',  label: 'Provenance Trace',  icon: ShieldCheck },
  { id: 'archive',     label: 'Archive Ops',       icon: Database },
];

export default function Navbar({ activeTab, setActiveTab, onBackToLanding }) {
  return (
    <header
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 100,
        height: '68px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 1.5rem',
        background: 'rgba(6, 9, 18, 0.45)',
        backdropFilter: 'blur(20px) saturate(180%)',
        WebkitBackdropFilter: 'blur(20px) saturate(180%)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
      }}
    >
      {/* Brand */}
      <div
        style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', cursor: 'pointer', flexShrink: 0 }}
        onClick={() => setActiveTab('search')}
      >
        <svg width="24" height="24" viewBox="0 0 256 256" fill="#ffffff" style={{ filter: 'drop-shadow(0 0 8px rgba(232, 112, 42, 0.5))' }}>
          <path d="M 256 256 L 128 256 L 0 128 L 128 128 Z M 256 128 L 128 128 L 0 0 L 128 0 Z" />
        </svg>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.45rem' }}>
          <span
            style={{
              fontSize: '1.35rem',
              color: '#ffffff',
              fontFamily: "'Playfair Display', serif",
              fontStyle: 'italic',
              fontWeight: 600,
              letterSpacing: '-0.02em',
            }}
          >
            GeoNexa
          </span>
          <span
            style={{
              fontSize: '0.62rem',
              color: '#e8702a',
              border: '1px solid rgba(232, 112, 42, 0.4)',
              background: 'rgba(232, 112, 42, 0.12)',
              borderRadius: '9999px',
              padding: '1px 6px',
              fontWeight: 600,
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
          background: 'rgba(255, 255, 255, 0.12)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          border: '1px solid rgba(255, 255, 255, 0.2)',
          borderRadius: '9999px',
          padding: '0.28rem 0.45rem',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)',
          overflow: 'auto',
          maxWidth: '65vw',
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
                padding: '0.38rem 0.9rem',
                borderRadius: '9999px',
                border: 'none',
                background: active ? 'rgba(255, 255, 255, 0.25)' : 'transparent',
                color: active ? '#ffffff' : 'rgba(255, 255, 255, 0.75)',
                fontWeight: active ? 600 : 500,
                fontSize: '0.8rem',
                cursor: 'pointer',
                transition: 'all 180ms ease',
                fontFamily: 'var(--font-sans)',
                whiteSpace: 'nowrap',
                boxShadow: active ? '0 2px 8px rgba(0,0,0,0.25)' : 'none',
              }}
              onMouseEnter={(e) => {
                if (!active) {
                  e.currentTarget.style.color = '#ffffff';
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.12)';
                }
              }}
              onMouseLeave={(e) => {
                if (!active) {
                  e.currentTarget.style.color = 'rgba(255, 255, 255, 0.75)';
                  e.currentTarget.style.background = 'transparent';
                }
              }}
            >
              <Icon size={13} color={active ? '#e8702a' : 'currentColor'} />
              <span>{label}</span>
            </button>
          );
        })}
      </nav>

      {/* Right side status & Home action */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            padding: '0.3rem 0.7rem',
            borderRadius: '9999px',
            background: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.35)',
            color: '#34d399',
            fontSize: '0.72rem',
            fontWeight: 600,
            letterSpacing: '0.04em',
          }}
        >
          <span
            className="pulse-indicator"
            style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#34d399', display: 'inline-block' }}
          />
          OFFLINE ACTIVE
        </div>

        {onBackToLanding && (
          <button
            onClick={onBackToLanding}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
              background: 'rgba(255, 255, 255, 0.08)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              color: 'rgba(255, 255, 255, 0.8)',
              borderRadius: '9999px',
              padding: '0.4rem 0.85rem',
              fontSize: '0.75rem',
              fontWeight: 500,
              cursor: 'pointer',
              fontFamily: 'var(--font-sans)',
              transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.18)';
              e.currentTarget.style.color = '#ffffff';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
              e.currentTarget.style.color = 'rgba(255, 255, 255, 0.8)';
            }}
          >
            <ArrowLeft size={12} />
            <span>Landing</span>
          </button>
        )}
      </div>
    </header>
  );
}
