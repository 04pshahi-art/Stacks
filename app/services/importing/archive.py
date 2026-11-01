"""Reading zip-based uploads (EPUB and .zip books) safely, entirely in memory."""
import posixpath
import zipfile
from urllib.parse import unquote

from .. import image_tokens
from ..text import clean_line
from .types import ParsedChapter, ParsedImage, UploadRejected

MAX_ENTRIES = 3000
MAX_TOTAL_BYTES = 80 * 1024 * 1024
MAX_ITEM_BYTES = 8 * 1024 * 1024


def check_archive(archive: zipfile.ZipFile, kind: str = "EPUB") -> None:
    """Refuse archives that are huge or have too many files (zip bombs)."""
    entries = archive.infolist()
    if len(entries) > MAX_ENTRIES:
        raise UploadRejected(f"That {kind} has too many files inside.")
    if sum(entry.file_size for entry in entries) > MAX_TOTAL_BYTES:
        raise UploadRejected(f"That {kind} is too large once unpacked.")


def read_bytes(archive: zipfile.ZipFile, name: str, limit: int = MAX_ITEM_BYTES) -> bytes:
    if archive.getinfo(name).file_size > limit:
        raise UploadRejected("One file inside that upload is too large.")
    return archive.read(name)


def read_text(archive: zipfile.ZipFile, name: str) -> str:
    return read_bytes(archive, name).decode("utf-8", errors="replace")


def member_path(base_dir: str, href: str) -> str | None:
    """Where `href` (relative to `base_dir`) lives inside the archive, or None if it
    points outside it or isn't a local file."""
    if not href or "://" in href or href.startswith(("data:", "/")):
        return None
    path = posixpath.normpath(posixpath.join(base_dir, unquote(href.split("#")[0])))
    return None if path.startswith(("..", "/")) else path


# ---- pictures found inside archives ---------------------------------------
MAX_PICTURES = 300
MAX_PICTURE_BYTES = 6 * 1024 * 1024
MAX_PICTURES_TOTAL_BYTES = 40 * 1024 * 1024
PICTURE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


class PictureCollector:
    """Reads pictures out of an archive, within limits, and hands out [[img:KEY]] keys.

    The same file used twice gets the same key. Pictures that are missing, too big or
    the wrong type are skipped: the book still imports, just without them.
    """

    def __init__(self, archive: zipfile.ZipFile):
        self.archive = archive
        self.names = set(archive.namelist())
        self.pictures: dict[str, ParsedImage] = {}
        self._keys: dict[str, str] = {}
        self._total = 0

    def add(self, path: str | None, alt: str = "") -> str | None:
        if not path or path not in self.names:
            return None
        if path in self._keys:
            return self._keys[path]
        if posixpath.splitext(path)[1].lower() not in PICTURE_EXTENSIONS:
            return None

        size = self.archive.getinfo(path).file_size
        too_many = len(self.pictures) >= MAX_PICTURES
        too_big = size > MAX_PICTURE_BYTES or self._total + size > MAX_PICTURES_TOTAL_BYTES
        if too_many or too_big:
            return None

        key = f"i{len(self.pictures) + 1}"
        self.pictures[key] = ParsedImage(self.archive.read(path), clean_line(alt, 300))
        self._keys[path] = key
        self._total += size
        return key


def with_pictures(title: str, body: str, pictures: dict[str, ParsedImage]) -> ParsedChapter:
    """A chapter that carries just the pictures its body points at."""
    used = {key: pictures[key] for key in image_tokens.keys_in(body) if key in pictures}
    return ParsedChapter(title, body, used)
