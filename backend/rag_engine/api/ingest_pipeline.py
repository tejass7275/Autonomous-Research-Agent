"""
ingest_pipeline.py (rag_engine.api)
Orchestrates the full ingestion flow for a search query: fetch paper
metadata -> download & parse PDFs -> chunk -> embed -> index into FAISS.
This is the single entry point Member 2's /api/papers or a background job
should call to populate the corpus; it hides the multi-step wiring between
the ingestion/, embeddings/, and chains/ subpackages.
"""

import logging
from typing import List, Optional

from rag_engine.ingestion.paper_fetcher import PaperFetcher, PaperMetadata
from rag_engine.ingestion.pdf_parser import PDFParser
from rag_engine.ingestion.chunker import DocumentChunker
from rag_engine.embeddings.embedder import Embedder
from rag_engine.embeddings.faiss_store import FAISSStore
from rag_engine.api.schemas import IngestRequest, IngestResult, IngestedPaperResult

logger = logging.getLogger(__name__)


class IngestPipeline:
    """
    Ties together fetching, parsing, chunking, embedding, and indexing into
    one call. Holds long-lived components (embedder, FAISS store) so they're
    initialized once rather than per-request.
    """

    def __init__(
        self,
        embedder: Embedder,
        store: FAISSStore,
        fetcher: Optional[PaperFetcher] = None,
        parser: Optional[PDFParser] = None,
        chunker: Optional[DocumentChunker] = None,
    ):
        self.embedder = embedder
        self.store = store
        self.fetcher = fetcher or PaperFetcher()
        self.parser = parser or PDFParser()
        self.chunker = chunker or DocumentChunker()

    def run(self, request: IngestRequest) -> IngestResult:
        """Fetch papers for a query and index each one that has a usable PDF."""
        papers = self.fetcher.fetch(request.query, sources=request.sources)
        papers = papers[: request.max_results]

        results: List[IngestedPaperResult] = []
        for paper in papers:
            results.append(self._ingest_single(paper))

        self.store.save()
        logger.info(
            "Ingest run complete for query='%s': %d/%d papers indexed",
            request.query, sum(1 for r in results if r.status == "indexed"), len(results),
        )
        return IngestResult(query=request.query, papers=results)

    def _ingest_single(self, paper: PaperMetadata) -> IngestedPaperResult:
        base_fields = dict(
            source_id=paper.source_id,
            source=paper.source,
            title=paper.title,
            authors=paper.authors,
            abstract=paper.abstract,
            pdf_url=paper.pdf_url,
            published_date=paper.published_date,
        )

        if not paper.pdf_url:
            logger.info("Skipping '%s' — no PDF URL available", paper.title[:60])
            return IngestedPaperResult(**base_fields, num_chunks_indexed=0, status="skipped_no_pdf")

        try:
            parsed = self.parser.parse_from_url(paper.source_id, paper.pdf_url)
            if parsed is None or not parsed.full_text.strip():
                return IngestedPaperResult(
                    **base_fields, num_chunks_indexed=0, status="failed",
                    error="PDF parsing returned no text",
                )

            chunks = self.chunker.chunk_document(
                paper.source_id, parsed.full_text, title=paper.title,
                extra_metadata={"source": paper.source},
            )
            if not chunks:
                return IngestedPaperResult(
                    **base_fields, num_chunks_indexed=0, status="failed",
                    error="Chunking produced no chunks",
                )

            embeddings = self.embedder.embed_texts([c.text for c in chunks])
            self.store.add(
                chunk_ids=[c.chunk_id for c in chunks],
                embeddings=embeddings,
                texts=[c.text for c in chunks],
                metadatas=[c.metadata for c in chunks],
            )

            return IngestedPaperResult(
                **base_fields, num_chunks_indexed=len(chunks), status="indexed",
            )

        except Exception as exc:  # keep one bad paper from failing the whole batch
            logger.error("Failed to ingest '%s': %s", paper.title[:60], exc)
            return IngestedPaperResult(
                **base_fields, num_chunks_indexed=0, status="failed", error=str(exc),
            )


if __name__ == "__main__":
    import logging as _logging

    _logging.basicConfig(level=_logging.INFO)

    embedder = Embedder()
    store = FAISSStore(embedding_dim=embedder.embedding_dim, index_path="data/faiss_index")
    store.load()

    pipeline = IngestPipeline(embedder, store)
    result = pipeline.run(IngestRequest(query="retrieval augmented generation", max_results=3))

    for p in result.papers:
        print(f"[{p.status}] {p.title[:60]} — {p.num_chunks_indexed} chunks")