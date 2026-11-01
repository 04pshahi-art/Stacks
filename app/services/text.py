"""Plain-text helpers shared by importers, forms and models."""
import re
import unicodedata

_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_BIDI_RE = re.compile("[‪-‮⁦-⁩​-‏]")
_EXTRA_BLANK_LINES_RE = re.compile(r"\n{3,}")
_PARAGRAPH_BREAK_RE = re.compile(r"\n\s*\n")
_WORD_RE = re.compile(r"\w+", re.UNICODE)


def clean_text(raw: str) -> str:
    """Normalise newlines, drop control characters, collapse extra blank lines."""
    text = unicodedata.normalize("NFC", raw)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_RE.sub("", text)
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return _EXTRA_BLANK_LINES_RE.sub("\n\n", text).strip()


def clean_line(raw: str, max_length: int) -> str:
    """One-line text (titles, names): no control or direction-spoofing characters."""
    text = _BIDI_RE.sub("", _CONTROL_RE.sub("", unicodedata.normalize("NFC", raw)))
    return " ".join(text.split())[:max_length]


def split_paragraphs(body: str) -> list[str]:
    return [" ".join(block.split()) for block in _PARAGRAPH_BREAK_RE.split(body) if block.strip()]


def count_words(text: str) -> int:
    return len(_WORD_RE.findall(text))
