// Dashboard.jsx
// Main research workflow screen: search bar up top, paper results grid,
// and a general-purpose insight panel for cross-paper questions. When a
// search returns no results, offers to fetch & index papers for that
// query directly from the UI (calls POST /api/papers/ingest).

import React, { useEffect, useState } from "react";
import SearchBar from "../components/SearchBar/SearchBar";
import PaperCard from "../components/PaperCard/PaperCard";
import InsightPanel from "../components/InsightPanel/InsightPanel";
import { usePaperSearch } from "../hooks/usePaperSearch";
import { useIngestPapers } from "../hooks/useIngestPapers";
import { listPapers } from "../api/client";

export default function Dashboard({ onSelectPaper }) {
  const { results, isLoading, error, lastQuery, search } = usePaperSearch();
  const { ingest, isIngesting, error: ingestError, lastResult: ingestResult } = useIngestPapers();
  const [recentPapers, setRecentPapers] = useState([]);
  const [isLoadingRecent, setIsLoadingRecent] = useState(true);

  const refreshRecentPapers = () => {
    setIsLoadingRecent(true);
    listPapers({ page: 1, pageSize: 12 })
      .then((data) => setRecentPapers(data.results))
      .catch(() => setRecentPapers([]))
      .finally(() => setIsLoadingRecent(false));
  };

  useEffect(() => {
    refreshRecentPapers();
  }, []);

  const handleIngestAndSearch = async () => {
    const result = await ingest(lastQuery, 10);
    if (result) {
      // Re-run the search now that the corpus has (hopefully) new matches,
      // and refresh the "recently indexed" grid in the background.
      await search(lastQuery);
      refreshRecentPapers();
    }
  };

  const showingSearchResults = lastQuery.length > 0;
  const showEmptyState = showingSearchResults && !isLoading && results.length === 0 && !error;

  return (
    <div className="dashboard">
      <header className="dashboard__header">
        <div className="dashboard__header-top">
          <div className="dashboard__header-text">
            <h1>Autonomous Research Agent</h1>
            <p className="dashboard__subtitle">
              Discover, analyze, and summarize academic papers with AI.
            </p>
          </div>
          <div className="dashboard__header-search">
            <SearchBar onSearch={search} isLoading={isLoading} />
          </div>
        </div>
      </header>

      <main className="dashboard__main">
        <section className="dashboard__results">
          <h2>{showingSearchResults ? `Results for "${lastQuery}"` : "Recently Indexed Papers"}</h2>

          {error && <p className="dashboard__error">{error}</p>}

          {(isLoading || isLoadingRecent) && <p>Loading...</p>}

          <div className="dashboard__grid">
            {showingSearchResults
              ? results.map((item, idx) => (
                  <PaperCard
                    key={item.paper.id || idx}
                    paper={item.paper}
                    matchScore={item.score}
                    onClick={onSelectPaper}
                  />
                ))
              : recentPapers.map((paper) => (
                  <PaperCard key={paper.id} paper={paper} onClick={onSelectPaper} />
                ))}
          </div>

          {showEmptyState && (
            <div className="dashboard__empty-state">
              <p className="dashboard__empty">
                No indexed papers match "{lastQuery}" yet.
              </p>
              <button
                onClick={handleIngestAndSearch}
                className="dashboard__ingest-button"
                disabled={isIngesting}
              >
                {isIngesting ? "Fetching & indexing papers..." : `Fetch & index papers on "${lastQuery}"`}
              </button>
              {ingestError && <p className="dashboard__error">{ingestError}</p>}
              {ingestResult && ingestResult.total === 0 && (
                <p className="dashboard__error">
                  No papers with a usable PDF were found for this topic. Try a broader query.
                </p>
              )}
            </div>
          )}
        </section>

        <aside className="dashboard__sidebar">
          <InsightPanel />
        </aside>
      </main>
    </div>
  );
}