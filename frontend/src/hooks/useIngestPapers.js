// useIngestPapers.js
// Encapsulates the ingest request lifecycle (loading/error/result) so the
// dashboard's "Fetch & Index" action just consumes state instead of
// managing fetch boilerplate.

import { useState, useCallback } from "react";
import { ingestPapers } from "../api/client";

export function useIngestPapers() {
  const [isIngesting, setIsIngesting] = useState(false);
  const [error, setError] = useState(null);
  const [lastResult, setLastResult] = useState(null);

  const ingest = useCallback(async (query, maxResults = 10) => {
    if (!query || !query.trim()) return null;

    setIsIngesting(true);
    setError(null);

    try {
      const data = await ingestPapers(query.trim(), maxResults);
      setLastResult(data);
      return data;
    } catch (err) {
      const message = err.response?.data?.detail || "Failed to fetch and index papers.";
      setError(message);
      return null;
    } finally {
      setIsIngesting(false);
    }
  }, []);

  return { ingest, isIngesting, error, lastResult };
}