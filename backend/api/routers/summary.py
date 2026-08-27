"""
summary.py
Endpoints for generating AI summaries of individual papers and answering
free-form questions grounded in the indexed corpus (RAG QA). Summaries are
cached on the Paper row so repeated requests don't re-call the LLM.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.models.paper import Paper
from api.models.query_log import QueryLog
from api.schemas.schemas import (
    SummaryRequest,
    SummaryResponse,
    QARequest,
    QAResponseSchema,
)
from api.core.security import get_current_user_id
from api.core.config import settings

# Member 1's RAG components
from rag_engine.llm.groq_client import GroqClient
from rag_engine.chains.summarization_chain import SummarizationChain
from rag_engine.chains.qa_chain import QAChain
from rag_engine.chains.retrieval_chain import RetrievalChain
from rag_engine.embeddings.embedder import Embedder
from rag_engine.embeddings.faiss_store import FAISSStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/summary", tags=["summary"])

# Lazily initialized singletons
_llm_client: GroqClient = None
_summarization_chain: SummarizationChain = None
_qa_chain: QAChain = None


def _get_summarization_chain() -> SummarizationChain:
    global _llm_client, _summarization_chain
    if _summarization_chain is None:
        _llm_client = GroqClient(api_key=settings.GROQ_API_KEY)
        _summarization_chain = SummarizationChain(_llm_client)
    return _summarization_chain


def _get_qa_chain() -> QAChain:
    global _llm_client, _qa_chain
    if _qa_chain is None:
        embedder = Embedder()
        store = FAISSStore(embedding_dim=embedder.embedding_dim, index_path=settings.FAISS_INDEX_PATH)
        store.load()
        retrieval_chain = RetrievalChain(embedder, store)
        if _llm_client is None:
            _llm_client = GroqClient(api_key=settings.GROQ_API_KEY)
        _qa_chain = QAChain(retrieval_chain, _llm_client)
    return _qa_chain


@router.post("", response_model=SummaryResponse)
def summarize_paper(
    request: SummaryRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Generate (or return cached) AI summary for a single paper."""
    paper = db.query(Paper).filter(Paper.id == request.paper_id).first()
    if paper is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    if paper.ai_summary and not request.force_regenerate:
        return SummaryResponse(
            paper_id=paper.id,
            paper_title=paper.title,
            summary=paper.ai_summary,
            was_cached=True,
        )

    if not paper.abstract:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paper has no abstract/text available to summarize",
        )

    chain = _get_summarization_chain()
    result = chain.summarize(paper.title, paper.abstract)

    paper.ai_summary = result.summary_text
    paper.summary_generated_at = datetime.now(timezone.utc)
    db.add(paper)

    db.add(
        QueryLog(
            user_id=user_id,
            paper_id=paper.id,
            query_type="summary",
            query_text=f"Summarize: {paper.title}",
            response_text=result.summary_text,
        )
    )
    db.commit()

    return SummaryResponse(
        paper_id=paper.id,
        paper_title=paper.title,
        summary=result.summary_text,
        was_cached=False,
    )


@router.post("/ask", response_model=QAResponseSchema)
def ask_question(
    request: QARequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Answer a free-form question using RAG, optionally scoped to a single paper."""
    source_id = None
    if request.paper_id:
        paper = db.query(Paper).filter(Paper.id == request.paper_id).first()
        if paper is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
        source_id = paper.source_id

    chain = _get_qa_chain()
    response = chain.answer(request.question, source_id=source_id)

    # Map returned chunk source_ids back to internal paper UUIDs
    source_ids = {r.metadata.get("source_id") for r in response.sources if r.metadata.get("source_id")}
    matched_papers = db.query(Paper).filter(Paper.source_id.in_(source_ids)).all() if source_ids else []

    db.add(
        QueryLog(
            user_id=user_id,
            paper_id=request.paper_id,
            query_type="qa",
            query_text=request.question,
            response_text=response.answer,
        )
    )
    db.commit()

    return QAResponseSchema(
        question=response.question,
        answer=response.answer,
        source_paper_ids=[p.id for p in matched_papers],
    )