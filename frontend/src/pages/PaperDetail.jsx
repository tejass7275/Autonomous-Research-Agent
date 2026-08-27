// PaperDetail.jsx
// Detail view for a single paper: full metadata, AI summary, and a
// paper-scoped Q&A panel.

import React, { useEffect, useState } from "react";
import SummaryView from "../components/SummaryView/SummaryView";
import InsightPanel from "../components/InsightPanel/InsightPanel";
import { getPaper } from "../api/client";

export default function PaperDetail({ paperId, onBack }) {
  const [paper, setPaper] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!paperId) return;
    setIsLoading(true);
    getPaper(paperId)
      .then(setPaper)
      .catch((err) => setError(err.response?.data?.detail || "Failed to load paper."))
      .finally(() => setIsLoading(false));
  }, [paperId]);

  if (isLoading) return <div className="paper-detail">Loading paper...</div>;
  if (error) return <div className="paper-detail paper-detail--error">{error}</div>;
  if (!paper) return null;

  return (
    <div className="paper-detail">
      <button onClick={onBack} className="paper-detail__back">
        &larr; Back to results
      </button>

      <header className="paper-detail__header">
        <span className="paper-detail__source">{paper.source}</span>
        <h1>{paper.title}</h1>
        <p className="paper-detail__authors">{paper.authors?.join(", ")}</p>
        {paper.published_date && (
          <p className="paper-detail__date">Published: {paper.published_date}</p>
        )}
        {paper.pdf_url && (
          <a href={paper.pdf_url} target="_blank" rel="noopener noreferrer" className="paper-detail__pdf-link">
            View original PDF
          </a>
        )}
      </header>

      <section className="paper-detail__abstract">
        <h3>Abstract</h3>
        <p>{paper.abstract}</p>
      </section>

      <section className="paper-detail__summary">
        <SummaryView paper={paper} />
      </section>

      <section className="paper-detail__qa">
        <InsightPanel paperId={paper.id} paperTitle={paper.title} />
      </section>
    </div>
  );
}
