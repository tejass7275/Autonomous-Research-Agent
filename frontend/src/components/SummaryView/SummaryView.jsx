// SummaryView.jsx
// Displays (and can trigger generation of) the AI summary for a single
// paper. Handles the loading/cached/regenerate states.

import React, { useState, useEffect, useCallback } from "react";
import { summarizePaper } from "../../api/client";
import "./SummaryView.css";

export default function SummaryView({ paper }) {
  const [summary, setSummary] = useState(paper?.ai_summary || null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [wasCached, setWasCached] = useState(!!paper?.ai_summary);

  const generateSummary = useCallback(
    async (forceRegenerate = false) => {
      if (!paper?.id) return;
      setIsLoading(true);
      setError(null);

      try {
        const result = await summarizePaper(paper.id, forceRegenerate);
        setSummary(result.summary);
        setWasCached(result.was_cached);
      } catch (err) {
        setError(err.response?.data?.detail || "Failed to generate summary.");
      } finally {
        setIsLoading(false);
      }
    },
    [paper?.id]
  );

  useEffect(() => {
    if (!summary && paper?.id) {
      generateSummary(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paper?.id]);

  if (isLoading) {
    return <div className="summary-view summary-view--loading">Generating AI summary...</div>;
  }

  if (error) {
    return (
      <div className="summary-view summary-view--error">
        <p>{error}</p>
        <button onClick={() => generateSummary(false)} className="summary-view__retry">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="summary-view">
      <div className="summary-view__header">
        <h4>AI Summary</h4>
        {wasCached && <span className="summary-view__badge">Cached</span>}
      </div>

      <div className="summary-view__content">
        {summary?.split("\n").map((line, idx) => (
          <p key={idx}>{line}</p>
        ))}
      </div>

      <button
        onClick={() => generateSummary(true)}
        className="summary-view__regenerate"
        disabled={isLoading}
      >
        Regenerate Summary
      </button>
    </div>
  );
}
