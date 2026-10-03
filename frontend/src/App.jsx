import React, { useState } from 'react';
import LandingPage from './components/LandingPage';
import Navbar from './components/Navbar';
import OverviewPage from './components/OverviewPage';
import SearchPage from './components/SearchPage';
import InvestigationPage from './components/InvestigationPage';
import ChangePage from './components/ChangePage';
import SimilarPage from './components/SimilarPage';
import ProvenancePage from './components/ProvenancePage';
import ArchivePage from './components/ArchivePage';

export default function App() {
  const [showLanding, setShowLanding] = useState(true);
  const [activeTab, setActiveTab] = useState('search');

  // Page-level state
  const [selectedTileId, setSelectedTileId] = useState(null);
  const [changeT1, setChangeT1] = useState(null);
  const [changeT2, setChangeT2] = useState(null);
  const [similarQueryTileId, setSimilarQueryTileId] = useState(null);
  const [selectedProvenanceId, setSelectedProvenanceId] = useState(null);
  const [searchInitialQuery, setSearchInitialQuery] = useState(null);

  const handleEnterPlatform = (tab) => {
    setShowLanding(false);
    if (tab && typeof tab === 'string') {
      setActiveTab(tab);
    }
    window.scrollTo({ top: 0 });
  };

  const handleBackToLanding = () => {
    setShowLanding(true);
    window.scrollTo({ top: 0 });
  };

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

  const handleTriggerSearchFromOverview = (queryText) => {
    setSearchInitialQuery(queryText);
    setActiveTab('search');
  };

  if (showLanding) {
    return <LandingPage onEnter={handleEnterPlatform} />;
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onBackToLanding={handleBackToLanding}
      />

      <main style={{ flex: 1, paddingBottom: '3rem' }}>
        {activeTab === 'overview' && (
          <OverviewPage
            setActiveTab={setActiveTab}
            onSelectSearchQuery={handleTriggerSearchFromOverview}
            onSelectTile={handleSelectTile}
            onSelectChangePair={handleSelectChangePair}
          />
        )}

        {activeTab === 'search' && (
          <SearchPage
            initialQuery={searchInitialQuery}
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
          <ProvenancePage initialProvenanceId={selectedProvenanceId} />
        )}
        {activeTab === 'archive' && <ArchivePage />}
      </main>

      <footer style={{
        borderTop: '1px solid var(--border-subtle)',
        padding: '1.1rem 2rem',
        textAlign: 'center',
        fontSize: '0.72rem',
        color: 'var(--text-dim)',
        background: 'rgba(6,9,18,0.92)',
        letterSpacing: '0.04em',
      }}>
        GeoNexa — Semantic Earth Observation Search & Intelligence Platform &nbsp;|&nbsp; Smart India Hackathon 2026 (SIH26227)
      </footer>
    </div>
  );
}
