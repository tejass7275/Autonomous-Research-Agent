"""
retrieval_chain.py
Context-aware semantic search: embeds a user query and retrieves the most
relevant chunks from the FAISS store. This is the core "find relevant
research papers" capability used by both the QA chain and the dashboard's
search endpoint.
"""

import logging
from typing import List, Optional

from rag_engine.embeddings.embedder import Embedder
from rag_engine.embeddings.faiss_store import FAISSStore, SearchResult

logger = logging.getLogger(__name__)


class RetrievalChain:
    """Combines the embedder and FAISS store into a single retrieval interface."""

    def __init__(self, embedder: Embedder, store: FAISSStore, default_top_k: int = 5):
        self.embedder = embedder
        self.store = store
        self.default_top_k = default_top_k

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        source_id: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Retrieve the top_k most semantically relevant chunks for a query.
        If source_id is provided, restrict results to chunks from that paper only
        (used for "ask a question about this specific paper" flows).
        """
        if not query or not query.strip():
            logger.warning("Empty query passed to retrieval chain")
            return []

        top_k = top_k or self.default_top_k
        query_embedding = self.embedder.embed_query(query)
        results = self.store.search(query_embedding, top_k=top_k, filter_source_id=source_id)

        logger.info("Retrieved %d chunks for query='%s'", len(results), query[:80])
        return results

    def retrieve_with_score_threshold(
        self, query: str, min_score: float = 0.3, top_k: Optional[int] = None
    ) -> List[SearchResult]:
        """Retrieve chunks but drop any below a minimum similarity score."""
        results = self.retrieve(query, top_k=top_k)
        filtered = [r for r in results if r.score >= min_score]
        if len(filtered) < len(results):
            logger.info(
                "Filtered out %d low-relevance chunks (min_score=%.2f)",
                len(results) - len(filtered), min_score,
            )
        return filtered


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    embedder = Embedder()
    store = FAISSStore(embedding_dim=embedder.embedding_dim, index_path="data/test_index")
    if not store.load():
        print("No index found — run the ingestion pipeline first.")
    else:
        chain = RetrievalChain(embedder, store)
        results = chain.retrieve("What is retrieval-augmented generation?")
        for r in results:
            print(f"[{r.score:.3f}] {r.text[:100]}")