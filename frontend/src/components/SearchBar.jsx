import { useState } from 'react';

export function SearchBar({ onSearch, loading }) {
    const [query, setQuery] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (query.trim()) {
            onSearch(query);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') {
            handleSubmit(e);
        }
    };

    return (
        <div className="search-container">
            <form className="search-box" onSubmit={handleSubmit}>
                <input
                    type="text"
                    className="search-input"
                    placeholder="Search runbooks, errors, symptoms..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={handleKeyDown}
                    autoFocus
                />
                <button
                    type="submit"
                    className="search-button"
                    disabled={loading || !query.trim()}
                >
                    {loading ? (
                        <>
                            <span className="button-spinner"></span>
                            Searching...
                        </>
                    ) : (
                        <>
                            Search
                            <span>→</span>
                        </>
                    )}
                </button>
            </form>
        </div>
    );
}
