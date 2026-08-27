"""
templates.py
Central location for all prompt templates used across the RAG chains.
Keeping these together makes prompt iteration and evaluation easier.
"""

from langchain.prompts import PromptTemplate

# ---------------------------------------------------------------------------
# Retrieval QA: answer a user's question using retrieved chunks as context
# ---------------------------------------------------------------------------
QA_SYSTEM_PROMPT = (
    "You are an academic research assistant. Answer the user's question using "
    "ONLY the provided paper excerpts as context. If the excerpts don't contain "
    "enough information to answer confidently, say so explicitly rather than "
    "guessing. Always cite which excerpt (by source title) supports each claim."
)

QA_PROMPT_TEMPLATE = PromptTemplate(
    input_variables=["context", "question"],
    template=(
        "Context excerpts from research papers:\n"
        "{context}\n\n"
        "Question: {question}\n\n"
        "Answer using only the context above. Cite source titles inline."
    ),
)


# ---------------------------------------------------------------------------
# Summarization: produce a structured summary of a single paper
# ---------------------------------------------------------------------------
SUMMARIZATION_SYSTEM_PROMPT = (
    "You are an expert research summarizer. Produce clear, structured summaries "
    "of academic papers for a technically literate but time-constrained reader."
)

SUMMARIZATION_PROMPT_TEMPLATE = PromptTemplate(
    input_variables=["paper_title", "paper_text"],
    template=(
        "Summarize the following research paper titled \"{paper_title}\".\n\n"
        "Paper content:\n{paper_text}\n\n"
        "Structure your summary with these sections:\n"
        "1. Problem: what problem does this paper address?\n"
        "2. Approach: what method/technique do they use?\n"
        "3. Key Findings: what are the main results?\n"
        "4. Limitations: what are the stated or apparent limitations?\n"
        "Keep the entire summary under 300 words."
    ),
)


# ---------------------------------------------------------------------------
# Insight generation: cross-paper insights for the dashboard
# ---------------------------------------------------------------------------
INSIGHT_SYSTEM_PROMPT = (
    "You are a research analyst identifying trends and connections across "
    "multiple papers. Be specific and avoid generic statements."
)

INSIGHT_PROMPT_TEMPLATE = PromptTemplate(
    input_variables=["paper_summaries"],
    template=(
        "Given the following paper summaries:\n{paper_summaries}\n\n"
        "Identify:\n"
        "1. Common themes or methods across these papers\n"
        "2. Any contradicting findings or approaches\n"
        "3. A suggested next research direction based on gaps you notice\n"
        "Be concise — 3-5 bullet points total."
    ),
)


def build_context_block(chunks: list) -> str:
    """
    Format retrieved chunks into a single context string for prompt injection.
    Each chunk is prefixed with its source title for citation purposes.
    """
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        title = chunk.metadata.get("title", "Unknown source") if hasattr(chunk, "metadata") else "Unknown source"
        text = chunk.text if hasattr(chunk, "text") else str(chunk)
        blocks.append(f"[{i}] Source: {title}\n{text}")
    return "\n\n".join(blocks)