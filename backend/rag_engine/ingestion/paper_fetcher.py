"""
paper_fetcher.py
Fetches academic papers from arXiv and Semantic Scholar based on a search query.
Returns normalized paper metadata (title, authors, abstract, pdf_url, source_id).
"""

import time
import logging
from dataclasses import dataclass, field
from typing import List, Optional

import requests
import feedparser

logger = logging.getLogger(__name__)

ARXIV_API_URL = "http://export.arxiv.org/api/query"
SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


@dataclass
class PaperMetadata:
    source_id: str
    title: str
    authors: List[str]
    abstract: str
    pdf_url: Optional[str]
    published_date: Optional[str]
    source: str  # "arxiv" | "semantic_scholar"
    extra: dict = field(default_factory=dict)


class PaperFetcher:
    """Fetches paper metadata from multiple academic sources."""

    def __init__(self, max_results: int = 10, request_timeout: int = 15):
        self.max_results = max_results
        self.request_timeout = request_timeout

    def fetch_from_arxiv(self, query: str) -> List[PaperMetadata]:
        """Query arXiv's public API and parse the Atom feed response."""
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": self.max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        try:
            response = requests.get(ARXIV_API_URL, params=params, timeout=self.request_timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("arXiv fetch failed: %s", exc)
            return []

        feed = feedparser.parse(response.text)
        papers = []
        for entry in feed.entries:
            pdf_url = next(
                (link.href for link in entry.links if getattr(link, "type", "") == "application/pdf"),
                None,
            )
            papers.append(
                PaperMetadata(
                    source_id=entry.id.split("/abs/")[-1],
                    title=entry.title.replace("\n", " ").strip(),
                    authors=[author.name for author in entry.authors],
                    abstract=entry.summary.replace("\n", " ").strip(),
                    pdf_url=pdf_url,
                    published_date=entry.published,
                    source="arxiv",
                )
            )
        return papers

    def fetch_from_semantic_scholar(self, query: str) -> List[PaperMetadata]:
        """Query Semantic Scholar's Graph API for papers matching the query."""
        params = {
            "query": query,
            "limit": self.max_results,
            "fields": "title,abstract,authors,url,openAccessPdf,publicationDate,paperId",
        }
        try:
            response = requests.get(
                SEMANTIC_SCHOLAR_API_URL, params=params, timeout=self.request_timeout
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Semantic Scholar fetch failed: %s", exc)
            return []

        data = response.json().get("data", [])
        papers = []
        for item in data:
            if not item.get("abstract"):
                continue
            pdf_info = item.get("openAccessPdf") or {}
            papers.append(
                PaperMetadata(
                    source_id=item.get("paperId", ""),
                    title=item.get("title", "").strip(),
                    authors=[a.get("name", "") for a in item.get("authors", [])],
                    abstract=item.get("abstract", "").strip(),
                    pdf_url=pdf_info.get("url"),
                    published_date=item.get("publicationDate"),
                    source="semantic_scholar",
                )
            )
        return papers

    def fetch(self, query: str, sources: Optional[List[str]] = None) -> List[PaperMetadata]:
        """
        Fetch and merge results from all requested sources.
        sources: subset of ["arxiv", "semantic_scholar"], defaults to both.
        """
        sources = sources or ["arxiv", "semantic_scholar"]
        results: List[PaperMetadata] = []

        if "arxiv" in sources:
            results.extend(self.fetch_from_arxiv(query))
            time.sleep(0.3)  # be polite to arXiv rate limits

        if "semantic_scholar" in sources:
            results.extend(self.fetch_from_semantic_scholar(query))

        deduped = self._deduplicate(results)
        logger.info("Fetched %d unique papers for query='%s'", len(deduped), query)
        return deduped

    @staticmethod
    def _deduplicate(papers: List[PaperMetadata]) -> List[PaperMetadata]:
        seen_titles = set()
        unique = []
        for paper in papers:
            key = paper.title.lower().strip()
            if key and key not in seen_titles:
                seen_titles.add(key)
                unique.append(paper)
        return unique


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetcher = PaperFetcher(max_results=5)
    results = fetcher.fetch("retrieval augmented generation")
    for p in results:
        print(f"[{p.source}] {p.title}")