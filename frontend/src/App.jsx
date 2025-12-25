import { useState, useCallback } from 'react';
import { SearchBar } from './components/SearchBar';
import { Filters } from './components/Filters';
import { ResultsList } from './components/ResultsList';
import { useSearch } from './hooks/useSearch';
import './index.css';

function App() {
  const { results, loading, error, performSearch } = useSearch();
  const [filters, setFilters] = useState({
    sourceTypes: null,
    projects: null,
  });
  const [lastQuery, setLastQuery] = useState('');

  const handleSearch = useCallback((query) => {
    setLastQuery(query);
    performSearch(query, filters);
  }, [filters, performSearch]);

  const handleFilterChange = useCallback((newFilters) => {
    setFilters(newFilters);
    if (lastQuery) {
      performSearch(lastQuery, newFilters);
    }
  }, [lastQuery, performSearch]);

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <a href="/" className="logo">
            <span className="logo-text">RunbookQuery</span>
          </a>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
            Hybrid Search for Careful Debugging
          </div>
        </div>
      </header>

      <main className="main">
        {!results && !loading && (
          <div className="hero">
            <h1 className="hero-title">
              Find the runbook you need, fast
            </h1>
            <p className="hero-subtitle">
              Search troubleshooting docs, runbooks, and GitHub issues with <br /> <u>hybrid BM25 + semantic search</u>
            </p>
          </div>
        )}

        <SearchBar onSearch={handleSearch} loading={loading} />

        <Filters filters={filters} onFilterChange={handleFilterChange} />

        {loading && (
          <div className="loading">
            <div className="spinner"></div>
            <span>Searching across runbooks...</span>
          </div>
        )}

        {error && (
          <div className="error-state">
            <strong>Error:</strong> {error}
            <div style={{ marginTop: '0.5rem', fontSize: '0.875rem' }}>
              Make sure the API server is running on localhost:8000
            </div>
          </div>
        )}

        {!loading && !error && <ResultsList results={results} />}
      </main>

      <footer className="footer">
        <div>
          RunbookQuery — Hybrid search powered by BM25 + Sentence Transformers + FAISS
        </div>
      </footer>
    </div>
  );
}

export default App;
