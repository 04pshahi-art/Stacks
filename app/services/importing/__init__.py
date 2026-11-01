"""Import books from uploaded files. The public entry point is parse_upload()."""
from pathlib import PurePath

from .book_zip import parse_zip
from .epub import parse_epub
from .pdf import parse_pdf
from .plain_text import parse_markdown, parse_text
from .types import MAX_TOTAL_CHARS, TOO_MUCH_TEXT, ParsedChapter, ParsedImage, ParsedUpload, UploadRejected

_PARSERS = {
    "txt": parse_text,
    "md": parse_markdown,
    "epub": parse_epub,
    "pdf": parse_pdf,
    "zip": parse_zip,
}

ALLOWED_EXTENSIONS = tuple(_PARSERS)

__all__ = [
    "ALLOWED_EXTENSIONS",
    "ParsedChapter",
    "ParsedImage",
    "ParsedUpload",
    "UploadRejected",
    "parse_upload",
]


def parse_upload(filename: str, data: bytes) -> ParsedUpload:
    """Parse an uploaded book into chapters, or raise UploadRejected.

    The file is only ever read in memory. It is never saved to disk or served
    back, so an upload can't be executed or used to reach other files.
    """
    extension = PurePath(filename or "").suffix.lower().lstrip(".")
    parser = _PARSERS.get(extension)
    if parser is None:
        allowed = ", ".join(f".{ext}" for ext in ALLOWED_EXTENSIONS)
        raise UploadRejected(f"Upload one of these file types: {allowed}.")
    if not data:
        raise UploadRejected("That file is empty.")
    parsed = parser(data)
    if sum(len(chapter.body) for chapter in parsed.chapters) > MAX_TOTAL_CHARS:
        raise UploadRejected(TOO_MUCH_TEXT)
    return parsed
