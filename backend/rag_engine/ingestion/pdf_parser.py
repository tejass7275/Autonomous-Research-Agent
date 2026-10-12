"""
pdf_parser.py
Downloads and extracts text from paper PDFs — fast and bounded.

Why this is written the way it is: parsing a full academic PDF with
pdfplumber can take 20-60+ seconds per paper, and a hung download can block
forever. For retrieval, the first ~12 pages (abstract, intro, method,
results) carry almost all of the useful signal, so this parser:

  * extracts with PyMuPDF (10-50x faster than pdfplumber) when installed,
    falling back to pdfplumber if it isn't;
  * only reads the first `max_pages` pages;
  * refuses PDFs larger than `max_bytes`;
  * enforces a total wall-clock budget on the download itself
    (requests' own timeout only limits idle time between bytes).
"""

import io
import re
import time
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import requests
import urllib3

try:  # PyMuPDF >= 1.24.3 exposes `pymupdf`; older versions expose `fitz`
    import pymupdf as _fitz
except ImportError:
    try:
        import fitz as _fitz
    except ImportError:
        _fitz = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

logger = logging.getLogger(__name__)

USER_AGENT = "AutonomousResearchAgent/1.0 (academic project; contact via repository)"


@dataclass
class ParsedDocument:
    source_id: str
    full_text: str
    num_pages: int
    title_guess: Optional[str] = None


class PDFParser:
    """Downloads a PDF from a URL (or reads local bytes) and extracts text."""

    def __init__(
        self,
        connect_timeout: int = 5,
        read_timeout: int = 15,
        download_budget_seconds: int = 25,
        max_pages: int = 12,
        max_bytes: int = 15 * 1024 * 1024,
    ):
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.download_budget_seconds = download_budget_seconds
        self.max_pages = max_pages
        self.max_bytes = max_bytes

        if _fitz is None and pdfplumber is None:
            logger.error("Neither PyMuPDF nor pdfplumber is installed — PDF parsing will fail")
        elif _fitz is None:
            logger.warning(
                "PyMuPDF not installed; falling back to slow pdfplumber. "
                "Run: pip install pymupdf"
            )

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------
    def download_pdf(self, pdf_url: str) -> Optional[bytes]:
        """Download a PDF, enforcing a size cap and a total time budget."""
        deadline = time.monotonic() + self.download_budget_seconds
        try:
            with requests.get(
                pdf_url,
                stream=True,
                timeout=(self.connect_timeout, self.read_timeout),
                headers={"User-Agent": USER_AGENT},
            ) as response:
                response.raise_for_status()

                declared = response.headers.get("Content-Length")
                if declared and declared.isdigit() and int(declared) > self.max_bytes:
                    logger.warning("Skipping %s — PDF is %s bytes (limit %d)", pdf_url, declared, self.max_bytes)
                    return None

                # NOTE: iter_content() blocks until a *full* chunk has arrived, so
                # a server trickling a few bytes at a time would never let us
                # check the deadline. read1() returns as soon as *any* data is
                # available, so the budget is checked on every read. (Falls
                # back to a small blocking read on older urllib3 versions.)
                raw = response.raw
                read_some = getattr(raw, "read1", None)

                buffer = bytearray()
                while True:
                    if read_some is not None:
                        block = read_some(64 * 1024, decode_content=True)
                    else:
                        block = raw.read(8 * 1024, decode_content=True)
                    if not block:
                        break

                    buffer.extend(block)
                    if len(buffer) > self.max_bytes:
                        logger.warning("Skipping %s — exceeded %d byte limit while downloading", pdf_url, self.max_bytes)
                        return None
                    if time.monotonic() > deadline:
                        logger.warning(
                            "Skipping %s — download exceeded %ds budget",
                            pdf_url, self.download_budget_seconds,
                        )
                        return None
                return bytes(buffer)
        except (requests.RequestException, urllib3.exceptions.HTTPError, OSError) as exc:
            # Reading the raw stream surfaces urllib3/socket errors directly
            # (e.g. ReadTimeoutError on a stalled server), not just requests' own.
            logger.warning("Failed to download PDF from %s: %s", pdf_url, exc)
            return None

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------
    def _extract_with_pymupdf(self, pdf_bytes: bytes) -> Tuple[List[str], int]:
        with _fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            total_pages = doc.page_count
            pages_text = [
                doc.load_page(i).get_text("text") or ""
                for i in range(min(total_pages, self.max_pages))
            ]
        return pages_text, total_pages

    def _extract_with_pdfplumber(self, pdf_bytes: bytes) -> Tuple[List[str], int]:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            total_pages = len(pdf.pages)
            pages_text = [
                (page.extract_text() or "") for page in pdf.pages[: self.max_pages]
            ]
        return pages_text, total_pages

    def parse_bytes(self, source_id: str, pdf_bytes: bytes) -> Optional[ParsedDocument]:
        try:
            if _fitz is not None:
                pages_text, total_pages = self._extract_with_pymupdf(pdf_bytes)
            elif pdfplumber is not None:
                pages_text, total_pages = self._extract_with_pdfplumber(pdf_bytes)
            else:
                return None

            full_text = self._clean_text("\n".join(pages_text))
            first_page = pages_text[0] if pages_text else ""
            title_guess = first_page.strip().split("\n")[0].strip() if first_page.strip() else None

            return ParsedDocument(
                source_id=source_id,
                full_text=full_text,
                num_pages=total_pages,
                title_guess=title_guess,
            )
        except Exception as exc:  # corrupt / encrypted / unusual PDFs raise many error types
            logger.warning("Failed to parse PDF for %s: %s", source_id, exc)
            return None

    def parse_from_url(self, source_id: str, pdf_url: str) -> Optional[ParsedDocument]:
        started = time.monotonic()
        pdf_bytes = self.download_pdf(pdf_url)
        if pdf_bytes is None:
            return None
        downloaded = time.monotonic()

        parsed = self.parse_bytes(source_id, pdf_bytes)
        logger.info(
            "PDF %s: download %.1fs, parse %.1fs, %d chars",
            source_id,
            downloaded - started,
            time.monotonic() - downloaded,
            len(parsed.full_text) if parsed else 0,
        )
        return parsed

    @staticmethod
    def _clean_text(text: str) -> str:
        """Remove common PDF extraction artifacts: hyphenated line breaks, excess whitespace."""
        text = text.replace("\x00", " ")
        text = re.sub(r"-\n(?=[a-z])", "", text)           # de-hyphenate wrapped words
        text = re.sub(r"\n{3,}", "\n\n", text)              # collapse excess blank lines
        text = re.sub(r"[ \t]{2,}", " ", text)               # collapse repeated spaces
        text = re.sub(r"(?<=[a-z])\n(?=[a-z])", " ", text)   # rejoin wrapped sentences
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
