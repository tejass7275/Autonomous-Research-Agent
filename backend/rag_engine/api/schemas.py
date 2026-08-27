"""
schemas.py (rag_engine.api)
Plain dataclass I/O contracts for the RAG service layer. Kept separate from
Member 2's Pydantic schemas (api/schemas/schemas.py) so rag_engine has no
dependency on FastAPI/Pydantic — it's a standalone Python package that
Member 2's routers happen to call into. Convert to/from Pydantic models at
the router boundary.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class IngestRequest:
    query: str
    sources: Optional[List[str]] = None  # ["arxiv", "semantic_scholar"], defaults to both
    max_results: int = 10


@dataclass
class IngestedPaperResult:
    source_id: str
    source: str
    title: str
    authors: List[str]
    abstract: str
    pdf_url: Optional[str]
    published_date: Optional[str]
    num_chunks_indexed: int
    status: str  # "indexed" | "skipped_no_pdf" | "failed"
    error: Optional[str] = None


@dataclass
class IngestResult:
    query: str
    papers: List[IngestedPaperResult] = field(default_factory=list)

    @property
    def succeeded_count(self) -> int:
        return sum(1 for p in self.papers if p.status == "indexed")


@dataclass
class SearchHit:
    chunk_text: str
    score: float
    source_id: str
    title: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchServiceResult:
    query: str
    hits: List[SearchHit] = field(default_factory=list)


@dataclass
class SummaryServiceResult:
    source_id: str
    title: str
    summary_text: str
    was_truncated: bool


@dataclass
class QAServiceResult:
    question: str
    answer: str
    source_ids: List[str] = field(default_factory=list)