from dataclasses import dataclass, field


# The most text one upload may hold (about 1.5 million words). Stops a small file that
# unpacks into an enormous amount of text from using up the server's memory.
MAX_TOTAL_CHARS = 8_000_000
TOO_MUCH_TEXT = "That book has too much text to import. Try splitting it into smaller files."


class UploadRejected(ValueError):
    """The uploaded file can't be imported. The message is safe to show the user."""


@dataclass(frozen=True)
class ParsedImage:
    """A picture found in an uploaded book. It is validated later, when it is stored."""

    data: bytes
    alt: str = ""


@dataclass(frozen=True)
class ParsedChapter:
    title: str
    body: str
    # Pictures the body points at with [[img:KEY]] lines, by KEY.
    images: dict[str, ParsedImage] = field(default_factory=dict)


@dataclass
class ParsedUpload:
    chapters: list[ParsedChapter]
    title: str = ""
    author: str = ""
    warnings: list[str] = field(default_factory=list)
