// Dashboard.jsx
// Main research workflow screen: search bar up top, paper results grid,
// and a general-purpose insight panel for cross-paper questions.

import React, { useEffect, useState } from "react";
import SearchBar from "../components/SearchBar/SearchBar";
import PaperCard from "../components/PaperCard/PaperCard";
import InsightPanel from "../components/InsightPanel/InsightPanel";
import { usePaperSearch } from "../hooks/usePaperSearch";
import { listPapers } from "../api/client";

export default function Dashboard({ onSelectPaper }) {
  const {
    results,
    isLoading,
    error,
    lastQuery,
    search,
  } = usePaperSearch();

  const [recentPapers, setRecentPapers] = useState([]);
  const [isLoadingRecent, setIsLoadingRecent] = useState(true);

  useEffect(() => {
    listPapers({ page: 1, pageSize: 12 })
      .then((data) => setRecentPapers(data.results || []))
      .catch(() => setRecentPapers([]))
      .finally(() => setIsLoadingRecent(false));
  }, []);

  const showingSearchResults = lastQuery.length > 0;

  const papersToShow = showingSearchResults
    ? results.map((item, idx) => ({
        ...item,
        _key: item.paper?.id || idx,
      }))
    : recentPapers.map((paper) => ({
        paper,
        _key: paper.id,
      }));

  return (
    <div className="dashboard">

      {/* =====================================
          HEADER
      ===================================== */}

      <header className="dashboard__header">

        <div className="dashboard__header-content">

          <div className="dashboard__brand">
            <div className="dashboard__logo">
              AI
            </div>

            <span>Autonomous Research Agent</span>
          </div>

          <div className="dashboard__hero">

            <span className="dashboard__eyebrow">
              AI-POWERED RESEARCH
            </span>

            <h1>
              Research smarter.
              <br />
              Discover insights faster.
            </h1>

            <p className="dashboard__subtitle">
              Discover, analyze, and summarize academic papers
              with the power of AI.
            </p>

          </div>

          {/* Search */}
          <div className="dashboard__search">
            <SearchBar
              onSearch={search}
              isLoading={isLoading}
            />
          </div>

        </div>

      </header>


      {/* =====================================
          MAIN CONTENT
      ===================================== */}

      <main className="dashboard__main">

        {/* Papers */}
        <section className="dashboard__results">

          <div className="section-header">

            <div>
              <span className="section-label">
                RESEARCH LIBRARY
              </span>

              <h2>
                {showingSearchResults
                  ? `Results for "${lastQuery}"`
                  : "Recently Indexed Papers"}
              </h2>
            </div>

            <span className="paper-count">
              {showingSearchResults
                ? `${results.length} papers`
                : `${recentPapers.length} papers`}
            </span>

          </div>


          {/* Error */}
          {error && (
            <div className="dashboard__error">
              <span className="error-icon">!</span>
              <span>{error}</span>
            </div>
          )}


          {/* Loading */}
          {(isLoading || isLoadingRecent) && (
            <div className="dashboard__loading">

              <div className="loading-spinner"></div>

              <span>
                {showingSearchResults
                  ? "Searching research papers..."
                  : "Loading indexed papers..."}
              </span>

            </div>
          )}


          {/* Papers */}
          {!isLoading &&
            !isLoadingRecent &&
            papersToShow.length > 0 && (

              <div className="dashboard__grid">

                {showingSearchResults

                  ? results.map((item, idx) => (
                      <PaperCard
                        key={item.paper?.id || idx}
                        paper={item.paper}
                        matchScore={item.score}
                        onClick={onSelectPaper}
                      />
                    ))

                  : recentPapers.map((paper) => (
                      <PaperCard
                        key={paper.id}
                        paper={paper}
                        onClick={onSelectPaper}
                      />
                    ))}

              </div>

            )}


          {/* Empty */}
          {showingSearchResults &&
            !isLoading &&
            results.length === 0 &&
            !error && (

              <div className="dashboard__empty">

                <div className="empty-icon">
                  ⌕
                </div>

                <h3>
                  No matching papers found
                </h3>

                <p>
                  Try using different keywords or a broader
                  research topic.
                </p>

              </div>

            )}

        </section>


        {/* =====================================
            AI INSIGHT SIDEBAR
        ===================================== */}

        <aside className="dashboard__sidebar">

          <div className="sidebar-header">

            <div className="sidebar-icon">
              ✦
            </div>

            <div>
              <span className="section-label">
                AI ASSISTANT
              </span>

              <h2>
                Research Assistant
              </h2>
            </div>

          </div>

          <p className="sidebar-description">
            Ask questions across your research papers and
            get AI-powered insights.
          </p>

          <InsightPanel />

        </aside>

      </main>


      {/* =====================================
          FOOTER
      ===================================== */}

      <footer className="dashboard__footer">
        <span>
          Autonomous Research Agent
        </span>

        <span>
          AI-powered academic research
        </span>
      </footer>

    </div>
  );
}