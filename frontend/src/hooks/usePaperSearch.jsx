// usePaperSearch.js
// Encapsulates the search request lifecycle (loading/error/results) so
// components just consume state instead of managing fetch boilerplate.

import { useState, useCallback } from "react";
import { searchPapers } from "../api/client";

export function usePaperSearch() {
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastQuery, setLastQuery] = useState("");

  const search = useCallback(async (query, options = {}) => {
    if (!query || !query.trim()) return;

    setIsLoading(true);
    setError(null);
    setLastQuery(query);

    try {
      const data = await searchPapers(query, options);
      setResults(data.results || []);
    } catch (err) {
      setError(err.response?.data?.detail || "Search failed. Please try again.");
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setResults([]);
    setError(null);
    setLastQuery("");
  }, []);

  return { results, isLoading, error, lastQuery, search, clear };
}
