"""
query_log.py
Logs every search/question a user makes, along with the AI's answer, so the
dashboard can show research history and let users revisit past sessions.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from api.db.database import Base


class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    paper_id = Column(UUID(as_uuid=True), ForeignKey("papers.id"), nullable=True)  # null for general searches

    query_type = Column(String(50), nullable=False)  # "search" | "qa" | "summary"
    query_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="query_logs")
    paper = relationship("Paper", back_populates="query_logs")

    def __repr__(self) -> str:
        return f"<QueryLog id={self.id} type={self.query_type}>"