"""Pictures inside chapter text.

Chapter text stays plain text. A picture is a paragraph that is exactly `[[img:KEY]]`.
While a file is being imported KEY is a short name such as `i1`. After the pictures are
saved it becomes the numeric id of the stored picture. Only the book's own pictures are
ever looked up, so typing a token in a chapter can't show anyone else's picture.
"""
import re
from collections.abc import Callable

_LINE_RE = re.compile(r"^\[\[img:(\w{1,12})\]\]$", re.MULTILINE)
MAX_ID_DIGITS = 9


def make(key: str) -> str:
    return f"[[img:{key}]]"


def key_of(paragraph: str) -> str | None:
    """The key if the whole paragraph is a picture token, else None."""
    match = _LINE_RE.match(paragraph.strip())
    return match.group(1) if match else None


def stored_id_of(paragraph: str) -> int | None:
    """The numeric picture id if the paragraph is a token for a stored picture."""
    key = key_of(paragraph)
    return int(key) if key and key.isdigit() and len(key) <= MAX_ID_DIGITS else None


def keys_in(text: str) -> list[str]:
    return _LINE_RE.findall(text)


def strip(text: str) -> str:
    """The text without picture lines (for counting words)."""
    return _LINE_RE.sub("", text)


def replace(text: str, mapper: Callable[[str], str | None]) -> str:
    """Rewrite each token. `mapper` returns the new key, or None to remove the picture."""

    def swap(match: re.Match) -> str:
        new_key = mapper(match.group(1))
        return make(new_key) if new_key else ""

    return _LINE_RE.sub(swap, text)
