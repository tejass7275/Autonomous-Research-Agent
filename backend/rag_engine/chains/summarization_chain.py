"""
summarization_chain.py
Generates structured, automated summaries of a single research paper using
the Groq LLM. Handles truncation for papers that exceed context limits.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from rag_engine.llm.groq_client import GroqClient
from rag_engine.prompts.templates import SUMMARIZATION_PROMPT_TEMPLATE, SUMMARIZATION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Rough character budget to stay within model context window alongside
# the prompt template and system prompt. Tune per model's actual limit.
MAX_INPUT_CHARS = 12000


@dataclass
class PaperSummary:
    paper_title: str
    summary_text: str
    was_truncated: bool


class SummarizationChain:
    """Produces a structured summary (Problem / Approach / Findings / Limitations)."""

    def __init__(self, llm_client: GroqClient):
        self.llm_client = llm_client

    def summarize(self, paper_title: str, paper_text: str) -> PaperSummary:
        if not paper_text or not paper_text.strip():
            logger.warning("Empty paper_text passed to summarizer for '%s'", paper_title)
            return PaperSummary(paper_title=paper_title, summary_text="", was_truncated=False)

        truncated = len(paper_text) > MAX_INPUT_CHARS
        input_text = paper_text[:MAX_INPUT_CHARS]

        prompt = SUMMARIZATION_PROMPT_TEMPLATE.format(
            paper_title=paper_title,
            paper_text=input_text,
        )

        messages = [
            {"role": "system", "content": SUMMARIZATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        summary_text = self.llm_client.chat(messages, temperature=0.2, max_tokens=500)

        if truncated:
            logger.info(
                "Paper '%s' truncated from %d to %d chars for summarization",
                paper_title, len(paper_text), MAX_INPUT_CHARS,
            )

        return PaperSummary(
            paper_title=paper_title,
            summary_text=summary_text,
            was_truncated=truncated,
        )

    def summarize_from_chunks(self, paper_title: str, chunk_texts: list) -> PaperSummary:
        """Convenience method when only chunked text is available (not the raw full text)."""
        combined_text = "\n\n".join(chunk_texts)
        return self.summarize(paper_title, combined_text)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = GroqClient()
    chain = SummarizationChain(client)

    sample_text = (
        "This paper introduces Retrieval-Augmented Generation (RAG), combining "
        "a pre-trained retriever with a pre-trained sequence-to-sequence model. "
        "Experiments show RAG outperforms purely parametric baselines on "
        "knowledge-intensive NLP tasks."
    )
    result = chain.summarize("Retrieval-Augmented Generation", sample_text)
    print(result.summary_text)