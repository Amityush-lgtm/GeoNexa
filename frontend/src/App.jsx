import React, { useState } from 'react';
import Navbar from './components/Navbar';
import SearchPage from './components/SearchPage';
import InvestigationPage from './components/InvestigationPage';
import ChangePage from './components/ChangePage';
import SimilarPage from './components/SimilarPage';
import ProvenancePage from './components/ProvenancePage';
import ArchivePage from './components/ArchivePage';

export default function App() {
  const [activeTab, setActiveTab] = useState('search');
  const [selectedTileId, setSelectedTileId] = useState(null);
  const [changeT1, setChangeT1] = useState(null);
  const [changeT2, setChangeT2] = useState(null);
  const [similarQueryTileId, setSimilarQueryTileId] = useState(null);
  const [selectedProvenanceId, setSelectedProvenanceId] = useState(null);

  const handleSelectTile = (tileId) => {
    setSelectedTileId(tileId);
    setActiveTab('investigate');
  };

  const handleSelectChangePair = (t1, t2) => {
    setChangeT1(t1);
    setChangeT2(t2 || null);
    setActiveTab('change');
  };

  const handleFindSimilar = (tileId) => {
    setSimilarQueryTileId(tileId);
    setActiveTab('similar');
  };

  const handleSelectProvenance = (provId) => {
    setSelectedProvenanceId(provId);
    setActiveTab('provenance');
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main style={{ flex: 1, paddingBottom: '3rem' }}>
        {activeTab === 'search' && (
          <SearchPage
            onSelectTile={handleSelectTile}
            onSelectChangePair={handleSelectChangePair}
            onSelectProvenance={handleSelectProvenance}
            setActiveTab={setActiveTab}
          />
        )}

        {activeTab === 'investigate' && (
          <InvestigationPage
            tileId={selectedTileId}
            onSelectChangePair={handleSelectChangePair}
            onFindSimilar={handleFindSimilar}
            onSelectProvenance={handleSelectProvenance}
            setActiveTab={setActiveTab}
          />
        )}

        {activeTab === 'change' && (
          <ChangePage
            t1TileId={changeT1}
            t2TileId={changeT2}
            onSelectProvenance={handleSelectProvenance}
            setActiveTab={setActiveTab}
          />
        )}

        {activeTab === 'similar' && (
          <SimilarPage
            queryTileId={similarQueryTileId}
            onSelectTile={handleSelectTile}
            onSelectChangePair={handleSelectChangePair}
            setActiveTab={setActiveTab}
          />
        )}

        {activeTab === 'provenance' && (
          <ProvenancePage
            initialProvenanceId={selectedProvenanceId}
          />
        )}

        {activeTab === 'archive' && (
          <ArchivePage />
        )}
      </main>

      <footer style={{ borderTop: '1px solid var(--border-subtle)', padding: '1.25rem 2rem', textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-dim)', background: 'rgba(10, 14, 23, 0.9)' }}>
        Smart India Hackathon 2026 — Problem Statement SIH26227 — Offline Semantic Satellite Retrieval & Multi-Temporal Change Platform
      </footer>
    </div>
  );
}
