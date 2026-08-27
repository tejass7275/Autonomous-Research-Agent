"""
search.py
Endpoints for discovering papers: fetching new papers from external sources
(arXiv/Semantic Scholar) and running semantic search over the indexed corpus.

NOTE: This router calls into Member 1's rag_engine package (retrieval_chain,
paper_fetcher). Those imports assume the rag_engine package is importable
from the backend root — adjust the import path if the final repo layout
differs.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.models.paper import Paper
from api.models.query_log import QueryLog
from api.schemas.schemas import SearchRequest, SearchResponse, SearchResultItem, PaperResponse
from api.core.security import get_current_user_id

# Member 1's RAG components
from rag_engine.chains.retrieval_chain import RetrievalChain
from rag_engine.embeddings.embedder import Embedder
from rag_engine.embeddings.faiss_store import FAISSStore
from api.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/search", tags=["search"])

# Lazily initialized singletons for the retrieval pipeline
_embedder: Embedder = None
_store: FAISSStore = None
_retrieval_chain: RetrievalChain = None


def _get_retrieval_chain() -> RetrievalChain:
    """Lazy-load the embedder/FAISS store once per process, not per request."""
    global _embedder, _store, _retrieval_chain
    if _retrieval_chain is None:
        _embedder = Embedder()
        _store = FAISSStore(embedding_dim=_embedder.embedding_dim, index_path=settings.FAISS_INDEX_PATH)
        if not _store.load():
            logger.warning("FAISS index not found at %s — search will return no results until ingested", settings.FAISS_INDEX_PATH)
        _retrieval_chain = RetrievalChain(_embedder, _store)
    return _retrieval_chain


@router.post("", response_model=SearchResponse)
def semantic_search(
    request: SearchRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Run context-aware semantic search over the indexed paper corpus and
    return matching chunks paired with their parent paper's metadata.
    """
    chain = _get_retrieval_chain()
    chunks = chain.retrieve(request.query, top_k=request.top_k)

    if not chunks:
        return SearchResponse(query=request.query, results=[])

    results = []
    for chunk in chunks:
        source_id = chunk.metadata.get("source_id")
        paper = db.query(Paper).filter(Paper.source_id == source_id).first()
        if paper is None:
            continue
        results.append(
            SearchResultItem(
                chunk_text=chunk.text,
                score=chunk.score,
                paper=PaperResponse.model_validate(paper),
            )
        )

    # Log the search for research history
    db.add(
        QueryLog(
            user_id=user_id,
            query_type="search",
            query_text=request.query,
            response_text=f"{len(results)} results",
        )
    )
    db.commit()

    return SearchResponse(query=request.query, results=results)


@router.get("/paper/{paper_id}", response_model=PaperResponse)
def get_paper_by_id(paper_id: UUID, db: Session = Depends(get_db)):
    """Fetch a single paper's metadata by its internal id."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if paper is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    return paper