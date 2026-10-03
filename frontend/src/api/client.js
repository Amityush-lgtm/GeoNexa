/**
 * API Client for interacting with the Semantic EO Search backend.
 */

const BASE_URL = '/api';

export async function searchArchive(params) {
  const res = await fetch(`${BASE_URL}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`Search failed: ${res.statusText}`);
  return res.json();
}

export async function searchSimilar(tileId, topK = 10) {
  const res = await fetch(`${BASE_URL}/search/similar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tile_id: tileId, top_k: topK }),
  });
  if (!res.ok) throw new Error(`Similarity search failed: ${res.statusText}`);
  return res.json();
}

export async function getTileDetails(tileId) {
  const res = await fetch(`${BASE_URL}/archive/tiles/${tileId}`);
  if (!res.ok) throw new Error(`Failed to load tile metadata: ${res.statusText}`);
  return res.json();
}

export function getTileImageUrl(tileId) {
  return `${BASE_URL}/archive/tiles/${tileId}/image`;
}

export async function getTemporalObservations(tileId) {
  const res = await fetch(`${BASE_URL}/change/temporal/${tileId}`);
  if (!res.ok) throw new Error(`Failed to load temporal observations: ${res.statusText}`);
  return res.json();
}

export async function analyzeChange(params) {
  const res = await fetch(`${BASE_URL}/change/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`Change analysis failed: ${res.statusText}`);
  return res.json();
}

export async function submitReview(params) {
  const res = await fetch(`${BASE_URL}/change/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`Review submission failed: ${res.statusText}`);
  return res.json();
}

export async function getProvenanceRecord(provenanceId) {
  const res = await fetch(`${BASE_URL}/provenance/${provenanceId}`);
  if (!res.ok) throw new Error(`Failed to load provenance record: ${res.statusText}`);
  return res.json();
}

export async function listRecentProvenance(limit = 20) {
  const res = await fetch(`${BASE_URL}/provenance?limit=${limit}`);
  if (!res.ok) throw new Error(`Failed to list provenance records: ${res.statusText}`);
  return res.json();
}

export async function getArchiveStats() {
  const res = await fetch(`${BASE_URL}/archive/stats`);
  if (!res.ok) throw new Error(`Failed to load archive stats: ${res.statusText}`);
  return res.json();
}

export async function listArchiveTiles(sceneId = null, limit = 60) {
  const url = sceneId 
    ? `${BASE_URL}/archive/tiles?scene_id=${encodeURIComponent(sceneId)}&limit=${limit}`
    : `${BASE_URL}/archive/tiles?limit=${limit}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to list tiles: ${res.statusText}`);
  return res.json();
}

export async function listScenes() {
  const res = await fetch(`${BASE_URL}/archive/scenes`);
  if (!res.ok) throw new Error(`Failed to list scenes: ${res.statusText}`);
  return res.json();
}

export async function getHealthStatus() {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error(`Failed to check health: ${res.statusText}`);
  return res.json();
}

export async function routeQuery(queryText) {
  const res = await fetch(`${BASE_URL}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: queryText }),
  });
  if (!res.ok) throw new Error(`Query routing failed: ${res.statusText}`);
  return res.json();
}
