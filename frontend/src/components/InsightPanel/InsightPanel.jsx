// InsightPanel.jsx
// Lets the user ask a free-form question (optionally scoped to one paper)
// and displays the AI-generated, RAG-grounded answer with source references.

import React, { useState } from "react";
import { askQuestion } from "../../api/client";

export default function InsightPanel({ paperId = null, paperTitle = null }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAsk = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    setIsLoading(true);
    setError(null);
    setAnswer(null);

    try {
      const response = await askQuestion(question.trim(), paperId);
      setAnswer(response);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to get an answer. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="insight-panel">
      <h4 className="insight-panel__heading">
        {paperTitle ? `Ask about "${paperTitle}"` : "Ask the research assistant"}
      </h4>

      <form onSubmit={handleAsk} className="insight-panel__form">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. What method did they use to evaluate results?"
          rows={3}
          className="insight-panel__textarea"
          disabled={isLoading}
        />
        <button
          type="submit"
          className="insight-panel__button"
          disabled={isLoading || !question.trim()}
        >
          {isLoading ? "Thinking..." : "Ask"}
        </button>
      </form>

      {error && <p className="insight-panel__error">{error}</p>}

      {answer && (
        <div className="insight-panel__answer">
          <p>{answer.answer}</p>
          {answer.source_paper_ids?.length > 0 && (
            <p className="insight-panel__sources">
              Grounded in {answer.source_paper_ids.length} source
              {answer.source_paper_ids.length > 1 ? "s" : ""}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
