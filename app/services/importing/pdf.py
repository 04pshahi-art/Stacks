"""PDF files with selectable text (scanned images are not supported)."""
import re
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import DependencyError, PyPdfError

from ..text import clean_line, clean_text, count_words
from .chaptering import MIN_WORDS_TO_KEEP
from .types import MAX_TOTAL_CHARS, TOO_MUCH_TEXT, ParsedChapter, ParsedUpload, UploadRejected

MAX_PAGES = 1500
PAGES_PER_CHAPTER = 12
LONG_PARAGRAPH_CHARS = 1200
TARGET_PARAGRAPH_CHARS = 700

_PARAGRAPH_BREAK_RE = re.compile(r"\n\s*\n")
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")


def _split_long(paragraph: str) -> list[str]:
    """PDFs often lack blank lines, so break very long runs at sentence ends."""
    if len(paragraph) <= LONG_PARAGRAPH_CHARS:
        return [paragraph]
    pieces, current = [], ""
    for sentence in _SENTENCE_END_RE.split(paragraph):
        current = f"{current} {sentence}".strip()
        if len(current) >= TARGET_PARAGRAPH_CHARS:
            pieces.append(current)
            current = ""
    if current:
        pieces.append(current)
    return pieces


def _reflow(raw: str) -> str:
    """Undo the hard line wraps PDFs carry so text can re-flow to any page size."""
    paragraphs = []
    for block in _PARAGRAPH_BREAK_RE.split(raw):
        joined = " ".join(block.replace("-\n", "").split())
        if joined:
            paragraphs.extend(_split_long(joined))
    return "\n\n".join(paragraphs)


def _extract_pages(reader: PdfReader) -> list[str]:
    """Read page text, stopping as soon as the total gets too large."""
    pages, total = [], 0
    for page in reader.pages:
        text = page.extract_text() or ""
        total += len(text)
        if total > MAX_TOTAL_CHARS:
            raise UploadRejected(TOO_MUCH_TEXT)
        pages.append(text)
    return pages


def _read_pages(data: bytes) -> tuple[list[str], str, str]:
    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            # Many PDFs are "encrypted" with an empty password (they open without
            # asking for one). Only a real password stops us.
            raise UploadRejected("This PDF needs a password to open, so it can't be imported.")
        if len(reader.pages) > MAX_PAGES:
            raise UploadRejected(f"That PDF has more than {MAX_PAGES} pages.")
        pages = _extract_pages(reader)
        meta = reader.metadata
        title = clean_line(str(meta.title or ""), 200) if meta else ""
        author = clean_line(str(meta.author or ""), 120) if meta else ""
    except UploadRejected:
        raise
    except (PyPdfError, DependencyError, ValueError, KeyError, OSError, RecursionError):
        raise UploadRejected("We couldn't read that PDF. It may be damaged.") from None
    return pages, title, author


def parse_pdf(data: bytes) -> ParsedUpload:
    if not data.startswith(b"%PDF-"):
        raise UploadRejected("That file isn't a valid PDF.")

    pages, title, author = _read_pages(data)
    chapters = []
    for start in range(0, len(pages), PAGES_PER_CHAPTER):
        end = min(start + PAGES_PER_CHAPTER, len(pages))
        body = clean_text(_reflow("\n\n".join(pages[start:end])))
        if count_words(body) >= MIN_WORDS_TO_KEEP:
            chapters.append(ParsedChapter(f"Pages {start + 1} to {end}", body))

    if not chapters:
        raise UploadRejected(
            "That PDF has no selectable text. Scanned PDFs need OCR before upload."
        )
    return ParsedUpload(chapters, title=title, author=author)
