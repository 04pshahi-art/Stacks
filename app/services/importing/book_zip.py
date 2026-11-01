"""A .zip containing one Markdown file and the pictures it points at.

    my-book.zip
    ├── book.md          (uses ![caption](images/map.png))
    └── images/map.png
"""
import posixpath
import zipfile
from io import BytesIO

from .archive import PictureCollector, check_archive, read_bytes
from .plain_text import decode_text, parse_markdown_text
from .types import ParsedUpload, UploadRejected

_MARKDOWN_SUFFIXES = (".md", ".markdown")


def _find_document(archive: zipfile.ZipFile) -> str:
    """The Markdown file to read: the one nearest the top of the zip."""
    candidates = [
        name
        for name in archive.namelist()
        if name.lower().endswith(_MARKDOWN_SUFFIXES)
        and not name.startswith("__MACOSX/")
        and not posixpath.basename(name).startswith(".")
    ]
    if not candidates:
        raise UploadRejected("Put one .md file (and its images) inside the ZIP.")
    return min(candidates, key=lambda name: (name.count("/"), name))


def parse_zip(data: bytes) -> ParsedUpload:
    if not zipfile.is_zipfile(BytesIO(data)):
        raise UploadRejected("That file isn't a valid ZIP.")

    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            check_archive(archive, "ZIP")
            document = _find_document(archive)
            text = decode_text(read_bytes(archive, document))
            return parse_markdown_text(text, PictureCollector(archive), posixpath.dirname(document))
    except zipfile.BadZipFile:
        raise UploadRejected("That ZIP is damaged.") from None
