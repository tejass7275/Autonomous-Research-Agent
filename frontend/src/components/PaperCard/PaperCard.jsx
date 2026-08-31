// PaperCard.jsx
// Displays a single paper's metadata (title, authors, abstract excerpt) as
// a clickable card. Used in search results and the paper explorer grid.

import React from "react";
import "./PaperCard.css";

function truncate(text, maxLength) {
  if (!text) return "";
  return text.length > maxLength ? `${text.slice(0, maxLength).trim()}...` : text;
}

export default function PaperCard({ paper, matchScore = null, onClick }) {
  return (
    <div
      className="paper-card"
      onClick={() => onClick?.(paper)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onClick?.(paper)}
    >
      <div className="paper-card__header">
        <span className="paper-card__source">{paper.source}</span>
        {matchScore !== null && (
          <span className="paper-card__score">{Math.round(matchScore * 100)}% match</span>
        )}
      </div>

      <h3 className="paper-card__title">{paper.title}</h3>

      <p className="paper-card__authors">
        {paper.authors?.slice(0, 3).join(", ")}
        {paper.authors?.length > 3 ? " et al." : ""}
      </p>

      <p className="paper-card__abstract">{truncate(paper.abstract, 200)}</p>

      {paper.ai_summary && (
        <div className="paper-card__badge">AI Summary Available</div>
      )}
    </div>
  );
}
