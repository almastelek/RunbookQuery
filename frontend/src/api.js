const API_BASE = 'http://localhost:8000';

export async function search(query, filters = {}, topK = 10) {
  const response = await fetch(`${API_BASE}/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      filters: {
        source_types: filters.sourceTypes || null,
        projects: filters.projects || null,
      },
      top_k: topK,
      include_scores: true,
    }),
  });

  if (!response.ok) {
    throw new Error(`Search failed: ${response.statusText}`);
  }

  return response.json();
}

export async function getHealth() {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.statusText}`);
  }
  return response.json();
}

export async function getMetrics() {
  const response = await fetch(`${API_BASE}/metrics`);
  if (!response.ok) {
    throw new Error(`Metrics fetch failed: ${response.statusText}`);
  }
  return response.json();
}
