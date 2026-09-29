import React from 'react';
import { Search, Compass, GitCompare, History, Database, ShieldCheck, Activity } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, offlineStatus }) {
  const navItems = [
    { id: 'search', label: 'Semantic Search', icon: Search },
    { id: 'investigate', label: 'Tile Inspector', icon: Compass },
    { id: 'change', label: 'Change Engine', icon: GitCompare },
    { id: 'similar', label: 'Site Similarity', icon: History },
    { id: 'provenance', label: 'Provenance Trace', icon: ShieldCheck },
    { id: 'archive', label: 'Archive Ops', icon: Database },
  ];

  return (
    <header className="glass-panel-elevated" style={{ margin: '1rem 1.5rem', padding: '0.85rem 1.5rem', borderRadius: '14px', position: 'sticky', top: '1rem', zIndex: 50 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }} onClick={() => setActiveTab('search')}>
          <div style={{
            background: 'linear-gradient(135deg, #06b6d4, #6366f1)',
            padding: '0.5rem',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 15px rgba(6, 182, 212, 0.4)'
          }}>
            <Activity size={22} color="#ffffff" />
          </div>
          <div>
            <div style={{ fontSize: '1.1rem', fontWeight: 800, letterSpacing: '-0.02em', background: 'linear-gradient(90deg, #f8fafc, #93c5fd)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              GeoNexa <span style={{ fontSize: '0.7rem', color: '#06b6d4', padding: '2px 6px', border: '1px solid rgba(6, 182, 212, 0.4)', borderRadius: '4px', verticalAlign: 'middle', WebkitTextFillColor: '#38bdf8' }}>SIH26227</span>
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              Semantic Earth Observation Search & Intelligence
            </div>
          </div>

        </div>

        {/* Navigation Tabs */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.45rem',
                  padding: '0.55rem 0.95rem',
                  borderRadius: '8px',
                  border: 'none',
                  background: isActive ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                  color: isActive ? '#38bdf8' : 'var(--text-muted)',
                  borderBottom: isActive ? '2px solid #38bdf8' : '2px solid transparent',
                  fontWeight: isActive ? 700 : 500,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                  transition: 'all var(--transition-fast)'
                }}
              >
                <Icon size={16} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Offline Readiness Badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <div className="badge badge-emerald" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.35rem 0.75rem' }}>
            <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#34d399', display: 'inline-block' }} className="pulse-indicator" />
            <span>OFFLINE ACTIVE</span>
          </div>
        </div>
      </div>
    </header>
  );
}
