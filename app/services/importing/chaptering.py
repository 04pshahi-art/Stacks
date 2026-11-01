"""Turn one long text into chapters."""
import re

from ..text import count_words, split_paragraphs
from .types import ParsedChapter, UploadRejected

MAX_CHAPTERS = 400
MAX_WORDS = 800_000
TARGET_WORDS_PER_CHAPTER = 2500
MIN_WORDS_TO_KEEP = 20
MAX_HEADING_LENGTH = 80

_HEADING_RE = re.compile(
    r"^(?:#{1,2}\s+(?P<markdown>.+?)|(?P<keyword>(?:chapter|part|book)\s+(?:\d+|[ivxlcdm]+)\b.*))\s*$",
    re.IGNORECASE,
)


def _heading_title(lines: list[str], index: int) -> str | None:
    """The chapter title if lines[index] is a standalone heading line."""
    line = lines[index].strip()
    if not line or len(line) > MAX_HEADING_LENGTH:
        return None
    follows_blank = index == 0 or not lines[index - 1].strip()
    precedes_blank = index + 1 >= len(lines) or not lines[index + 1].strip()
    match = _HEADING_RE.match(line)
    if not (match and follows_blank and precedes_blank):
        return None
    return (match.group("markdown") or match.group("keyword")).strip()


def _split_on_headings(lines: list[str], heading_indexes: list[int]) -> list[ParsedChapter]:
    chapters = []
    boundaries = heading_indexes + [len(lines)]

    preface = "\n".join(lines[: heading_indexes[0]]).strip()
    if count_words(preface) >= MIN_WORDS_TO_KEEP:
        chapters.append(ParsedChapter("Preface", preface))

    for start, end in zip(boundaries, boundaries[1:]):
        title = _heading_title(lines, start)
        body = "\n".join(lines[start + 1 : end]).strip()
        if count_words(body) >= MIN_WORDS_TO_KEEP:
            chapters.append(ParsedChapter(title, body))
    return chapters


def _split_by_length(text: str) -> list[ParsedChapter]:
    groups, current, current_words = [], [], 0
    for paragraph in split_paragraphs(text):
        current.append(paragraph)
        current_words += count_words(paragraph)
        if current_words >= TARGET_WORDS_PER_CHAPTER:
            groups.append(current)
            current, current_words = [], 0
    if current:
        groups.append(current)
    return [
        ParsedChapter(f"Chapter {number}", "\n\n".join(group))
        for number, group in enumerate(groups, start=1)
    ]


def split_into_chapters(text: str) -> list[ParsedChapter]:
    """Split on 'Chapter N' / '# Heading' lines, or into even parts if there are none."""
    if count_words(text) > MAX_WORDS:
        raise UploadRejected(f"That book is longer than {MAX_WORDS:,} words.")

    lines = text.split("\n")
    heading_indexes = [i for i in range(len(lines)) if _heading_title(lines, i)]
    chapters = (
        _split_on_headings(lines, heading_indexes)
        if len(heading_indexes) >= 2
        else _split_by_length(text)
    )

    if not chapters:
        raise UploadRejected("We couldn't find any readable text in that file.")
    if len(chapters) > MAX_CHAPTERS:
        raise UploadRejected(f"That file has more than {MAX_CHAPTERS} chapters.")
    return chapters
