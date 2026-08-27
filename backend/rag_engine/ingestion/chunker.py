"""
chunker.py
Splits parsed document text into overlapping chunks suitable for embedding
and retrieval. Uses LangChain's RecursiveCharacterTextSplitter with
paragraph/sentence-aware separators tuned for academic paper text.
"""

import logging
import hashlib
from dataclasses import dataclass, field
from typing import List, Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    chunk_id: str
    source_id: str
    text: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)


class DocumentChunker:
    """
    Splits document text into chunks.

    Defaults (chunk_size=1000, chunk_overlap=150) are a reasonable starting
    point for academic text with GTE/MiniLM-style embedding models. Tune
    these based on retrieval quality evaluation.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
        )

    def chunk_document(
        self,
        source_id: str,
        text: str,
        title: Optional[str] = None,
        extra_metadata: Optional[dict] = None,
    ) -> List[Chunk]:
        if not text or not text.strip():
            logger.warning("Empty text passed to chunker for source_id=%s", source_id)
            return []

        raw_chunks = self.splitter.split_text(text)
        chunks = []
        for idx, raw_chunk in enumerate(raw_chunks):
            chunk_id = self._make_chunk_id(source_id, idx)
            metadata = {"title": title, "chunk_index": idx, "source_id": source_id}
            if extra_metadata:
                metadata.update(extra_metadata)

            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    source_id=source_id,
                    text=raw_chunk,
                    chunk_index=idx,
                    metadata=metadata,
                )
            )

        logger.info("Split source_id=%s into %d chunks", source_id, len(chunks))
        return chunks

    @staticmethod
    def _make_chunk_id(source_id: str, index: int) -> str:
        raw = f"{source_id}-{index}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample_text = (
        "Retrieval-Augmented Generation combines a retriever with a generator. "
        "This allows models to ground responses in external knowledge. " * 50
    )
    chunker = DocumentChunker(chunk_size=300, chunk_overlap=50)
    result = chunker.chunk_document("sample-001", sample_text, title="Sample Paper")
    print(f"Created {len(result)} chunks")
    print(result[0])