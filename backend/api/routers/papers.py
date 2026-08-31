"""
papers.py
CRUD/listing endpoints for papers stored in Postgres. Handles pagination
for the dashboard's paper explorer view, and paper creation from fetched
metadata (called after Member 1's ingestion pipeline runs).
"""

import logging
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from api.db.database import get_db
from api.models.paper import Paper
from api.schemas.schemas import PaperBase, PaperResponse, PaperListResponse
from api.core.security import get_current_user_id
from api.core.config import settings

# Member 1's RAG service facade
from rag_engine.api.service import get_rag_service, RAGService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/papers", tags=["papers"])


def _get_service() -> RAGService:
    return get_rag_service(settings.FAISS_INDEX_PATH, settings.GROQ_API_KEY)


@router.get("", response_model=PaperListResponse)
def list_papers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    source: Optional[str] = Query(default=None, description="Filter by source: arxiv | semantic_scholar"),
    db: Session = Depends(get_db),
):
    """List papers with pagination, newest first. Used by the dashboard's paper grid."""
    query = db.query(Paper)
    if source:
        query = query.filter(Paper.source == source)

    total = query.count()
    papers = (
        query.order_by(Paper.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaperListResponse(total=total, page=page, page_size=page_size, results=papers)


@router.get("/{paper_id}", response_model=PaperResponse)
def get_paper(paper_id: UUID, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if paper is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    return paper


@router.post("", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
def create_paper(
    paper_data: PaperBase,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Persist a paper's metadata. Called after fetching from arXiv/Semantic
    Scholar (via Member 1's paper_fetcher) to store it before/while it gets
    chunked and indexed into FAISS.
    """
    existing = db.query(Paper).filter(Paper.source_id == paper_data.source_id).first()
    if existing:
        return existing

    paper = Paper(**paper_data.model_dump())
    db.add(paper)
    try:
        db.commit()
        db.refresh(paper)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Paper with this source_id already exists",
        )

    return paper


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paper(
    paper_id: UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if paper is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    db.delete(paper)
    db.commit()
    return None


@router.post("/ingest", response_model=PaperListResponse, status_code=status.HTTP_201_CREATED)
def ingest_papers(
    query: str = Query(..., min_length=1, max_length=500, description="Topic to fetch and index papers for"),
    max_results: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    service: RAGService = Depends(_get_service),
):
    """
    Single entry point for populating the corpus: fetches papers for a query,
    indexes them into FAISS, AND persists their metadata to Postgres.

    This replaces running `python -m rag_engine.api.ingest_pipeline` as a
    separate manual step — that script only writes to FAISS, so papers
    indexed that way never show up in /api/search (which requires a
    matching Postgres row). Use this endpoint instead so both stores stay
    in sync automatically.
    """
    result = service.ingest(query, max_results=max_results)

    saved_papers = []
    for paper_result in result.papers:
        if paper_result.status != "indexed":
            logger.info("Skipping Postgres insert for '%s' (status=%s)", paper_result.title[:60], paper_result.status)
            continue

        existing = db.query(Paper).filter(Paper.source_id == paper_result.source_id).first()
        if existing:
            saved_papers.append(existing)
            continue

        paper = Paper(
            source_id=paper_result.source_id,
            source=paper_result.source,
            title=paper_result.title,
            authors=paper_result.authors,
            abstract=paper_result.abstract,
            pdf_url=paper_result.pdf_url,
            published_date=paper_result.published_date,
            is_indexed="indexed",
        )
        db.add(paper)
        try:
            db.commit()
            db.refresh(paper)
            saved_papers.append(paper)
        except IntegrityError:
            db.rollback()
            existing = db.query(Paper).filter(Paper.source_id == paper_result.source_id).first()
            if existing:
                saved_papers.append(existing)

    logger.info(
        "Ingest complete for query='%s': %d/%d papers saved to Postgres",
        query, len(saved_papers), len(result.papers),
    )

    return PaperListResponse(
        total=len(saved_papers),
        page=1,
        page_size=len(saved_papers) or 1,
        results=saved_papers,
    )