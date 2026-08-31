"""
summary.py
Endpoints for generating AI summaries of individual papers and answering
free-form questions grounded in the indexed corpus (RAG QA). Delegates to
rag_engine.api.service.RAGService. Summaries are cached on the Paper row
so repeated requests don't re-call the LLM.
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

# Member 1's RAG service facade
from rag_engine.api.service import get_rag_service, RAGService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/summary", tags=["summary"])


def _get_service() -> RAGService:
    return get_rag_service(settings.FAISS_INDEX_PATH, settings.GROQ_API_KEY)


@router.post("", response_model=SummaryResponse)
def summarize_paper(
    request: SummaryRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    service: RAGService = Depends(_get_service),
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

    result = service.summarize(paper.source_id, paper.title, paper.abstract)

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
    service: RAGService = Depends(_get_service),
):
    """Answer a free-form question using RAG, optionally scoped to a single paper."""
    source_id = None
    if request.paper_id:
        paper = db.query(Paper).filter(Paper.id == request.paper_id).first()
        if paper is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
        source_id = paper.source_id

    result = service.ask(request.question, source_id=source_id)

    matched_papers = (
        db.query(Paper).filter(Paper.source_id.in_(result.source_ids)).all()
        if result.source_ids else []
    )

    db.add(
        QueryLog(
            user_id=user_id,
            paper_id=request.paper_id,
            query_type="qa",
            query_text=request.question,
            response_text=result.answer,
        )
    )
    db.commit()

    return QAResponseSchema(
        question=result.question,
        answer=result.answer,
        source_paper_ids=[p.id for p in matched_papers],
    )