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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/papers", tags=["papers"])


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