"""
schemas.py
Pydantic request/response models for the API. Kept in one file since the
schema set is small; split by domain (paper_schemas.py, etc.) if it grows.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: Optional[str]
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---------------------------------------------------------------------------
# Papers
# ---------------------------------------------------------------------------
class PaperBase(BaseModel):
    title: str
    authors: List[str] = []
    abstract: Optional[str] = None
    pdf_url: Optional[str] = None
    published_date: Optional[str] = None
    source: str
    source_id: str


class PaperResponse(PaperBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ai_summary: Optional[str] = None
    is_indexed: str
    created_at: datetime


class PaperListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: List[PaperResponse]


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------
class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    sources: Optional[List[str]] = None  # e.g. ["arxiv", "semantic_scholar"]
    top_k: int = Field(default=10, ge=1, le=50)


class SearchResultItem(BaseModel):
    chunk_text: str
    score: float
    paper: PaperResponse


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]


# ---------------------------------------------------------------------------
# Summary / QA
# ---------------------------------------------------------------------------
class SummaryRequest(BaseModel):
    paper_id: UUID
    force_regenerate: bool = False


class SummaryResponse(BaseModel):
    paper_id: UUID
    paper_title: str
    summary: str
    was_cached: bool


class QARequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    paper_id: Optional[UUID] = None  # restrict Q&A to a single paper if set


class QAResponseSchema(BaseModel):
    question: str
    answer: str
    source_paper_ids: List[UUID] = []


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------
class QueryLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    query_type: str
    query_text: str
    response_text: Optional[str]
    paper_id: Optional[UUID]
    created_at: datetime


class HistoryListResponse(BaseModel):
    total: int
    results: List[QueryLogResponse]