"""EPUB files.

An EPUB is a zip of XHTML. We read it with the standard-library HTML parser
instead of an XML parser, which avoids XML entity-expansion attacks, and we cap
archive size so a zip bomb can't exhaust memory.
"""
import posixpath
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from io import BytesIO

from .. import image_tokens
from ..text import clean_line, clean_text, count_words
from .archive import PictureCollector, check_archive, member_path, read_text, with_pictures
from .chaptering import MAX_CHAPTERS, MIN_WORDS_TO_KEEP
from .types import ParsedUpload, UploadRejected

_BLOCK_TAGS = {
    "p", "div", "br", "li", "blockquote", "section", "article", "tr",
    "h1", "h2", "h3", "h4", "h5", "h6",
}
_HEADING_TAGS = {"h1", "h2", "h3"}
_SKIPPED_TAGS = {"script", "style", "head", "svg", "nav"}


@dataclass(frozen=True)
class _ImageRef:
    src: str
    alt: str


class _PackageParser(HTMLParser):
    """Reads container.xml and the OPF package file (tag-based, no XML parser)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rootfile = ""
        self.manifest: dict[str, str] = {}
        self.spine: list[str] = []
        self.meta = {"dc:title": "", "dc:creator": ""}
        self._capturing = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "rootfile":
            self.rootfile = self.rootfile or attributes.get("full-path", "")
        elif tag == "item" and attributes.get("id") and attributes.get("href"):
            self.manifest[attributes["id"]] = attributes["href"]
        elif tag == "itemref" and attributes.get("idref"):
            self.spine.append(attributes["idref"])
        elif tag in self.meta:
            self._capturing = tag

    def handle_endtag(self, tag):
        if tag == self._capturing:
            self._capturing = None

    def handle_data(self, data):
        if self._capturing and not self.meta[self._capturing]:
            self.meta[self._capturing] = data


class _ChapterText(HTMLParser):
    """Collects paragraphs, pictures and the first heading from one XHTML document."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.blocks: list[str | _ImageRef] = []
        self._buffer: list[str] = []
        self._skip_depth = 0

    def _take_buffer(self) -> str:
        text = " ".join("".join(self._buffer).split())
        self._buffer = []
        return text

    def handle_starttag(self, tag, attrs):
        if tag in _SKIPPED_TAGS:
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS:
            self._flush()
        elif tag == "img" and not self._skip_depth:
            self._flush()
            attributes = dict(attrs)
            self.blocks.append(_ImageRef(attributes.get("src") or "", attributes.get("alt") or ""))

    def handle_endtag(self, tag):
        if tag in _SKIPPED_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag in _BLOCK_TAGS:
            self._flush(is_heading=tag in _HEADING_TAGS)

    def handle_data(self, data):
        if not self._skip_depth:
            self._buffer.append(data)

    def _flush(self, is_heading: bool = False):
        text = self._take_buffer()
        if not text:
            return
        if is_heading and not self.title:
            self.title = clean_line(text, 200)
        else:
            self.blocks.append(text)

    def render(self, collector: PictureCollector, base_dir: str) -> str:
        """The chapter as text, with [[img:KEY]] lines where usable pictures were."""
        parts = []
        for block in self.blocks:
            if isinstance(block, _ImageRef):
                key = collector.add(member_path(base_dir, block.src), block.alt)
                if key:
                    parts.append(image_tokens.make(key))
            else:
                parts.append(block)
        return clean_text("\n\n".join(parts))


def _parse_package(archive: zipfile.ZipFile) -> tuple[_PackageParser, str]:
    try:
        container = _PackageParser()
        container.feed(read_text(archive, "META-INF/container.xml"))
        package = _PackageParser()
        package.feed(read_text(archive, container.rootfile))
    except KeyError:
        raise UploadRejected("That EPUB is missing its table of contents.") from None
    return package, posixpath.dirname(container.rootfile)


def parse_epub(data: bytes) -> ParsedUpload:
    if not zipfile.is_zipfile(BytesIO(data)):
        raise UploadRejected("That file isn't a valid EPUB.")

    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            check_archive(archive)
            package, base_dir = _parse_package(archive)
            collector = PictureCollector(archive)
            chapters = []
            for idref in package.spine:
                path = member_path(base_dir, package.manifest.get(idref, ""))
                if not path or path not in collector.names:
                    continue
                reader = _ChapterText()
                reader.feed(read_text(archive, path))
                body = reader.render(collector, posixpath.dirname(path))
                if count_words(image_tokens.strip(body)) >= MIN_WORDS_TO_KEEP:
                    title = reader.title or f"Chapter {len(chapters) + 1}"
                    chapters.append(with_pictures(title, body, collector.pictures))
                if len(chapters) > MAX_CHAPTERS:
                    raise UploadRejected(f"That EPUB has more than {MAX_CHAPTERS} chapters.")
    except zipfile.BadZipFile:
        raise UploadRejected("That EPUB is damaged.") from None

    if not chapters:
        raise UploadRejected("We couldn't find any readable text in that EPUB.")
    return ParsedUpload(
        chapters,
        title=clean_line(package.meta["dc:title"], 200),
        author=clean_line(package.meta["dc:creator"], 120),
    )
