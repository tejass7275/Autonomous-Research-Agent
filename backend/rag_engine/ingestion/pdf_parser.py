"""
pdf_parser.py
Downloads and extracts clean text (plus basic structure) from paper PDFs.
Uses pdfplumber for extraction quality on academic layouts (multi-column, tables).
"""

import re
import io
import logging
from dataclasses import dataclass
from typing import Optional

import requests
import pdfplumber

logger = logging.getLogger(__name__)


@dataclass
class ParsedDocument:
    source_id: str
    full_text: str
    num_pages: int
    title_guess: Optional[str] = None


class PDFParser:
    """Downloads a PDF from a URL (or reads local bytes) and extracts text."""

    def __init__(self, request_timeout: int = 30):
        self.request_timeout = request_timeout

    def download_pdf(self, pdf_url: str) -> Optional[bytes]:
        try:
            response = requests.get(pdf_url, timeout=self.request_timeout)
            response.raise_for_status()
            return response.content
        except requests.RequestException as exc:
            logger.error("Failed to download PDF from %s: %s", pdf_url, exc)
            return None

    def parse_bytes(self, source_id: str, pdf_bytes: bytes) -> Optional[ParsedDocument]:
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                pages_text = []
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    pages_text.append(text)

                full_text = "\n".join(pages_text)
                full_text = self._clean_text(full_text)
                title_guess = pages_text[0].split("\n")[0].strip() if pages_text else None

                return ParsedDocument(
                    source_id=source_id,
                    full_text=full_text,
                    num_pages=len(pdf.pages),
                    title_guess=title_guess,
                )
        except Exception as exc:  # pdfplumber can raise various parsing errors
            logger.error("Failed to parse PDF for %s: %s", source_id, exc)
            return None

    def parse_from_url(self, source_id: str, pdf_url: str) -> Optional[ParsedDocument]:
        pdf_bytes = self.download_pdf(pdf_url)
        if pdf_bytes is None:
            return None
        return self.parse_bytes(source_id, pdf_bytes)

    @staticmethod
    def _clean_text(text: str) -> str:
        """Remove common PDF extraction artifacts: hyphenated line breaks, excess whitespace."""
        text = re.sub(r"-\n(?=[a-z])", "", text)          # de-hyphenate wrapped words
        text = re.sub(r"\n{3,}", "\n\n", text)             # collapse excess blank lines
        text = re.sub(r"[ \t]{2,}", " ", text)              # collapse repeated spaces
        text = re.sub(r"(?<=[a-z])\n(?=[a-z])", " ", text)  # rejoin wrapped sentences
        return text.strip()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = PDFParser()
    doc = parser.parse_from_url(
        "test-paper",
        "https://arxiv.org/pdf/2005.11401.pdf",  # RAG paper as a smoke test
    )
    if doc:
        print(f"Parsed {doc.num_pages} pages, {len(doc.full_text)} chars")
        print(doc.full_text[:500])