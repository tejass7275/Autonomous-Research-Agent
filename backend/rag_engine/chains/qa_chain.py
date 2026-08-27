"""
qa_chain.py
End-to-end RAG question-answering: retrieves relevant chunks for a question,
builds a grounded context block, and asks the LLM to answer using only that
context. This is the main chain the FastAPI /summary and /search endpoints
call into for "AI-generated insights".
"""

import logging
from dataclasses import dataclass
from typing import List, Optional

from rag_engine.chains.retrieval_chain import RetrievalChain
from rag_engine.llm.groq_client import GroqClient
from rag_engine.prompts.templates import (
    QA_PROMPT_TEMPLATE,
    QA_SYSTEM_PROMPT,
    build_context_block,
)
from rag_engine.embeddings.faiss_store import SearchResult

logger = logging.getLogger(__name__)


@dataclass
class QAResponse:
    question: str
    answer: str
    sources: List[SearchResult]


class QAChain:
    """Retrieval-augmented question answering over the indexed paper corpus."""

    def __init__(self, retrieval_chain: RetrievalChain, llm_client: GroqClient, top_k: int = 5):
        self.retrieval_chain = retrieval_chain
        self.llm_client = llm_client
        self.top_k = top_k

    def answer(self, question: str, source_id: Optional[str] = None) -> QAResponse:
        """
        Answer a question using RAG.
        source_id: optionally restrict retrieval to a single paper (for
        "ask about this paper" flows on the dashboard).
        """
        retrieved_chunks = self.retrieval_chain.retrieve(
            question, top_k=self.top_k, source_id=source_id
        )

        if not retrieved_chunks:
            logger.info("No relevant chunks found for question='%s'", question[:80])
            return QAResponse(
                question=question,
                answer="I couldn't find any relevant content in the indexed papers to answer this question.",
                sources=[],
            )

        context = build_context_block(retrieved_chunks)
        prompt = QA_PROMPT_TEMPLATE.format(context=context, question=question)

        messages = [
            {"role": "system", "content": QA_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        answer_text = self.llm_client.chat(messages, temperature=0.2, max_tokens=600)

        return QAResponse(
            question=question,
            answer=answer_text,
            sources=retrieved_chunks,
        )


if __name__ == "__main__":
    import logging as _logging
    from rag_engine.embeddings.embedder import Embedder
    from rag_engine.embeddings.faiss_store import FAISSStore

    _logging.basicConfig(level=_logging.INFO)

    embedder = Embedder()
    store = FAISSStore(embedding_dim=embedder.embedding_dim, index_path="data/test_index")
    if not store.load():
        print("No index found — run the ingestion pipeline first.")
    else:
        retrieval_chain = RetrievalChain(embedder, store)
        llm_client = GroqClient()
        qa_chain = QAChain(retrieval_chain, llm_client)

        response = qa_chain.answer("What problem does retrieval-augmented generation solve?")
        print("Answer:", response.answer)
        print("\nSources:")
        for s in response.sources:
            print(f"  [{s.score:.3f}] {s.metadata.get('title')}")