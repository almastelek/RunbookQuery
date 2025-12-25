import { ResultCard } from './ResultCard';

export function ResultsList({ results }) {
    if (!results) {
        return (
            <div className="empty-state">
                <div className="empty-icon">🔎</div>
                <h3 className="empty-title">Start searching</h3>
                <p className="empty-description">
                    Search for error codes, symptoms, or troubleshooting topics to find relevant runbooks and documentation.
                </p>
                <div style={{ marginTop: '1.5rem', color: 'var(--color-text-muted)', fontSize: '0.875rem' }}>
                    <strong>Try:</strong> "CrashLoopBackOff", "OOMKilled exit code 137", or "503 upstream error"
                </div>
            </div>
        );
    }

    if (results.results.length === 0) {
        return (
            <div className="empty-state">
                <div className="empty-icon">😕</div>
                <h3 className="empty-title">No results found</h3>
                <p className="empty-description">
                    Try different keywords or check your filters.
                </p>
            </div>
        );
    }

    return (
        <div className="results-section">
            <div className="results-header">
                <span className="results-count">
                    Found <strong>{results.total_results}</strong> result{results.total_results !== 1 ? 's' : ''}
                </span>
                <div className="results-meta">
                    <span className="meta-item">
                        ⚡ {results.latency_ms.toFixed(0)}ms
                    </span>
                    <span className="meta-item">
                        🔀 {results.retrieval_mode}
                    </span>
                    {results.cache_hit && (
                        <span className="meta-item" style={{ color: 'var(--color-success)' }}>
                            💾 cached
                        </span>
                    )}
                </div>
            </div>

            {results.results.map((result, index) => (
                <ResultCard key={result.chunk_id} result={result} rank={index + 1} />
            ))}
        </div>
    );
}
