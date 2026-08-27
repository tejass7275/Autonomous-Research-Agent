"""
paper.py
Stores paper metadata fetched/ingested from arXiv or Semantic Scholar,
plus cached AI-generated summaries so they don't need regenerating on
every dashboard view.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, DateTime, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from api.db.database import Base


class Paper(Base):
    __tablename__ = "papers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(String(255), unique=True, nullable=False, index=True)  # arXiv id / S2 paperId
    source = Column(String(50), nullable=False)  # "arxiv" | "semantic_scholar"

    title = Column(String(1000), nullable=False)
    authors = Column(ARRAY(String), default=list)
    abstract = Column(Text, nullable=True)
    pdf_url = Column(String(1000), nullable=True)
    published_date = Column(String(50), nullable=True)

    # Cached AI-generated summary (populated after first summarization request)
    ai_summary = Column(Text, nullable=True)
    summary_generated_at = Column(DateTime(timezone=True), nullable=True)

    # Whether this paper's chunks have been embedded into the FAISS index
    is_indexed = Column(String(20), default="pending")  # "pending" | "indexed" | "failed"

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    query_logs = relationship("QueryLog", back_populates="paper")

    def __repr__(self) -> str:
        return f"<Paper id={self.id} title={self.title[:50]!r}>"