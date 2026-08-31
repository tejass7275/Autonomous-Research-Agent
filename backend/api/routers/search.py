"""
search.py
Endpoints for running semantic search over the indexed corpus. Delegates
all RAG work to rag_engine.api.service.RAGService — no direct dependency
on embedder/FAISS internals here.

Note: results are filtered against Postgres (a FAISS hit is only returned
if a matching Paper row exists). Use POST /api/papers/ingest to populate
both stores together — the standalone `python -m rag_engine.api.ingest_pipeline`
script only writes to FAISS and will leave search results empty.
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
from api.core.config import settings

# Member 1's RAG service facade
from rag_engine.api.service import get_rag_service, RAGService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/search", tags=["search"])


def _get_service() -> RAGService:
    return get_rag_service(settings.FAISS_INDEX_PATH, settings.GROQ_API_KEY)


@router.post("", response_model=SearchResponse)
def semantic_search(
    request: SearchRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    service: RAGService = Depends(_get_service),
):
    """
    Run context-aware semantic search over the indexed paper corpus and
    return matching chunks paired with their parent paper's metadata.
    """
    result = service.search(request.query, top_k=request.top_k)

    if not result.hits:
        return SearchResponse(query=request.query, results=[])

    results = []
    skipped = 0
    for hit in result.hits:
        paper = db.query(Paper).filter(Paper.source_id == hit.source_id).first()
        if paper is None:
            skipped += 1
            continue
        results.append(
            SearchResultItem(
                chunk_text=hit.chunk_text,
                score=hit.score,
                paper=PaperResponse.model_validate(paper),
            )
        )

    if skipped:
        logger.warning(
            "Skipped %d FAISS hit(s) with no matching Postgres row — "
            "run POST /api/papers/ingest instead of the standalone ingest script",
            skipped,
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