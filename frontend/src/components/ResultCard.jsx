import { useState } from 'react';

export function ResultCard({ result, rank }) {
    const [showScores, setShowScores] = useState(false);

    const formatScore = (score) => {
        if (score === null || score === undefined) return '--';
        return score.toFixed(4);
    };

    const handleClick = () => {
        if (result.url && !result.url.startsWith('file://')) {
            window.open(result.url, '_blank');
        }
    };

    return (
        <div className="result-card" onClick={handleClick}>
            <div className="result-header">
                <a
                    className="result-title"
                    href={result.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                >
                    {result.title}
                </a>
                <span className="result-rank">#{rank}</span>
            </div>

            <div className="result-meta">
                <span className={`result-chip chip-${result.source_type}`}>
                    {result.source_type === 'docs' ? '📄' : '🐛'} {result.source_type}
                </span>
                {result.project && result.project !== 'unknown' && (
                    <span className="result-chip chip-project">
                        {result.project}
                    </span>
                )}
            </div>

            <div
                className="result-snippet"
                dangerouslySetInnerHTML={{ __html: result.snippet }}
            />

            <div className="result-url">{result.url}</div>

            {result.scores && (
                <>
                    <div
                        className="score-toggle"
                        onClick={(e) => {
                            e.stopPropagation();
                            setShowScores(!showScores);
                        }}
                    >
                        <span>{showScores ? '▼' : '▶'}</span>
                        <span>Score breakdown</span>
                        <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)' }}>
                            {formatScore(result.scores.final_score)}
                        </span>
                    </div>

                    {showScores && (
                        <div className="score-breakdown">
                            <div className="score-item">
                                <span className="score-label">BM25 Score</span>
                                <span className="score-value bm25">
                                    {formatScore(result.scores.bm25_score)}
                                    {result.scores.bm25_rank && (
                                        <span style={{ opacity: 0.6, fontSize: '0.75rem' }}>
                                            {' '}(rank #{result.scores.bm25_rank})
                                        </span>
                                    )}
                                </span>
                            </div>
                            <div className="score-item">
                                <span className="score-label">Vector Score</span>
                                <span className="score-value vector">
                                    {formatScore(result.scores.vector_score)}
                                    {result.scores.vector_rank && (
                                        <span style={{ opacity: 0.6, fontSize: '0.75rem' }}>
                                            {' '}(rank #{result.scores.vector_rank})
                                        </span>
                                    )}
                                </span>
                            </div>
                            <div className="score-item">
                                <span className="score-label">Final (RRF)</span>
                                <span className="score-value final">
                                    {formatScore(result.scores.final_score)}
                                </span>
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
