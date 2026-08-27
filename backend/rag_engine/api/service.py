"""
service.py (rag_engine.api)
The main facade Member 2's FastAPI routers should import from. Wraps the
embedder, FAISS store, and all chains behind three simple methods (search,
summarize, ask) plus ingest, so routers never touch rag_engine internals
directly. Instantiate one RAGService per process (see `get_rag_service`)
rather than per-request — model loading and index loading are expensive.
"""

import logging
import threading
from typing import List, Optional

from rag_engine.embeddings.embedder import Embedder
from rag_engine.embeddings.faiss_store import FAISSStore
from rag_engine.llm.groq_client import GroqClient
from rag_engine.chains.retrieval_chain import RetrievalChain
from rag_engine.chains.summarization_chain import SummarizationChain
from rag_engine.chains.qa_chain import QAChain
from rag_engine.api.ingest_pipeline import IngestPipeline
from rag_engine.api.schemas import (
    IngestRequest,
    IngestResult,
    SearchHit,
    SearchServiceResult,
    SummaryServiceResult,
    QAServiceResult,
)

logger = logging.getLogger(__name__)


class RAGService:
    """
    Facade over the full RAG pipeline. Construct once at app startup:

        rag_service = RAGService(
            faiss_index_path=settings.FAISS_INDEX_PATH,
            groq_api_key=settings.GROQ_API_KEY,
        )

    and reuse it across requests via a FastAPI dependency (see
    `get_rag_service` below).
    """

    def __init__(
        self,
        faiss_index_path: str = "data/faiss_index",
        groq_api_key: Optional[str] = None,
        retrieval_top_k: int = 5,
    ):
        logger.info("Initializing RAGService (index_path=%s)", faiss_index_path)

        self.embedder = Embedder()
        self.store = FAISSStore(embedding_dim=self.embedder.embedding_dim, index_path=faiss_index_path)
        if not self.store.load():
            logger.warning(
                "No existing FAISS index at %s — call ingest() to populate it before searching",
                faiss_index_path,
            )

        self.llm_client = GroqClient(api_key=groq_api_key)

        self.retrieval_chain = RetrievalChain(self.embedder, self.store, default_top_k=retrieval_top_k)
        self.summarization_chain = SummarizationChain(self.llm_client)
        self.qa_chain = QAChain(self.retrieval_chain, self.llm_client, top_k=retrieval_top_k)
        self.ingest_pipeline = IngestPipeline(self.embedder, self.store)

    # -- Ingestion -----------------------------------------------------
    def ingest(self, query: str, sources: Optional[List[str]] = None, max_results: int = 10) -> IngestResult:
        """Fetch, parse, chunk, embed, and index papers matching a query."""
        request = IngestRequest(query=query, sources=sources, max_results=max_results)
        return self.ingest_pipeline.run(request)

    # -- Search ----------------------------------------------------------
    def search(self, query: str, top_k: int = 10, source_id: Optional[str] = None) -> SearchServiceResult:
        """Semantic search over the indexed corpus."""
        results = self.retrieval_chain.retrieve(query, top_k=top_k, source_id=source_id)
        hits = [
            SearchHit(
                chunk_text=r.text,
                score=r.score,
                source_id=r.metadata.get("source_id", ""),
                title=r.metadata.get("title"),
                metadata=r.metadata,
            )
            for r in results
        ]
        return SearchServiceResult(query=query, hits=hits)

    # -- Summarization -----------------------------------------------------
    def summarize(self, source_id: str, title: str, text: str) -> SummaryServiceResult:
        """Generate a structured summary for a paper's text (abstract or full text)."""
        result = self.summarization_chain.summarize(title, text)
        return SummaryServiceResult(
            source_id=source_id,
            title=title,
            summary_text=result.summary_text,
            was_truncated=result.was_truncated,
        )

    # -- Question answering ------------------------------------------------
    def ask(self, question: str, source_id: Optional[str] = None) -> QAServiceResult:
        """Answer a question using RAG, optionally scoped to a single paper."""
        response = self.qa_chain.answer(question, source_id=source_id)
        source_ids = list({r.metadata.get("source_id") for r in response.sources if r.metadata.get("source_id")})
        return QAServiceResult(question=response.question, answer=response.answer, source_ids=source_ids)


# ---------------------------------------------------------------------------
# Process-wide singleton so FastAPI routers share one instance instead of
# reloading the embedding model / FAISS index on every request.
# ---------------------------------------------------------------------------
_service_instance: Optional[RAGService] = None
_service_lock = threading.Lock()


def get_rag_service(
    faiss_index_path: str = "data/faiss_index",
    groq_api_key: Optional[str] = None,
) -> RAGService:
    """
    Thread-safe lazy singleton accessor. Use as a FastAPI dependency:

        def get_service():
            return get_rag_service(settings.FAISS_INDEX_PATH, settings.GROQ_API_KEY)

        @router.post("/search")
        def search(request: SearchRequest, service: RAGService = Depends(get_service)):
            return service.search(request.query, top_k=request.top_k)
    """
    global _service_instance
    if _service_instance is None:
        with _service_lock:
            if _service_instance is None:  # re-check inside the lock
                _service_instance = RAGService(faiss_index_path, groq_api_key)
    return _service_instance


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    service = get_rag_service()

    result = service.search("what is retrieval augmented generation?")
    for hit in result.hits:
        print(f"[{hit.score:.3f}] {hit.title}: {hit.chunk_text[:80]}")