"""TXT and Markdown files."""
import re
from collections.abc import Callable

from .. import image_tokens
from ..text import clean_text
from .archive import PictureCollector, member_path, with_pictures
from .chaptering import split_into_chapters
from .types import ParsedUpload, UploadRejected

_EMPHASIS_RES = (
    re.compile(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1"),
    re.compile(r"(\*|_)(?=\S)(.+?)(?<=\S)\1"),
)
_BLOCKQUOTE_RE = re.compile(r"^>\s?", re.MULTILINE)
# A line that is only an image: ![alt](path "optional title")
_IMAGE_LINE_RE = re.compile(
    r'^[ \t]*!\[([^\]]*)\]\([ \t]*<?([^)\s>]+)>?(?:[ \t]+"[^"]*")?[ \t]*\)[ \t]*$', re.MULTILINE
)
_INLINE_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")


def decode_text(data: bytes) -> str:
    if b"\x00" in data[:8192]:
        raise UploadRejected("That file doesn't look like plain text.")
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UploadRejected("We couldn't read that file's text encoding. Save it as UTF-8.")


def _strip_markdown(text: str) -> str:
    """Remove emphasis and quote markers; heading lines are kept for chaptering."""
    text = _BLOCKQUOTE_RE.sub("", text)
    for pattern in _EMPHASIS_RES:
        text = pattern.sub(r"\2", text)
    return text


def _place_images(text: str, add_picture: Callable[[str, str], str | None]) -> str:
    """Turn image-only lines into picture tokens. Pictures that can't be found are
    dropped, and images inside a sentence are replaced by their alt text.

    Done before emphasis is stripped, so underscores in file names survive."""

    def swap(match: re.Match) -> str:
        key = add_picture(match.group(2), match.group(1))
        return f"\n\n{image_tokens.make(key)}\n\n" if key else ""

    return _INLINE_IMAGE_RE.sub(r"\1", _IMAGE_LINE_RE.sub(swap, text))


def parse_markdown_text(
    text: str, collector: PictureCollector | None = None, base_dir: str = ""
) -> ParsedUpload:
    """Markdown to chapters. With a `collector`, local images are kept as pictures."""

    def add_picture(src: str, alt: str) -> str | None:
        return collector.add(member_path(base_dir, src), alt) if collector else None

    body = clean_text(_strip_markdown(_place_images(text, add_picture)))
    pictures = collector.pictures if collector else {}
    chapters = split_into_chapters(body)
    return ParsedUpload([with_pictures(c.title, c.body, pictures) for c in chapters])


def parse_text(data: bytes) -> ParsedUpload:
    return ParsedUpload(split_into_chapters(clean_text(decode_text(data))))


def parse_markdown(data: bytes) -> ParsedUpload:
    return parse_markdown_text(decode_text(data))
