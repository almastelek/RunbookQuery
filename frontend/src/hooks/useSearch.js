import { useState, useCallback } from 'react';
import { search } from '../api';

export function useSearch() {
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const performSearch = useCallback(async (query, filters = {}, topK = 10) => {
        if (!query.trim()) {
            setResults(null);
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const data = await search(query, filters, topK);
            setResults(data);
        } catch (err) {
            setError(err.message);
            setResults(null);
        } finally {
            setLoading(false);
        }
    }, []);

    const clearResults = useCallback(() => {
        setResults(null);
        setError(null);
    }, []);

    return {
        results,
        loading,
        error,
        performSearch,
        clearResults,
    };
}
