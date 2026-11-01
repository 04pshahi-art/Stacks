"""Safe handling of uploaded pictures, shared by covers and pictures inside books.

Every picture is decoded and re-encoded as a JPEG with Pillow. That strips metadata
and any payload hidden in the original file. Pictures are stored under random file
names and are only ever served through an access-checked route.
"""
import re
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from flask import current_app, g
from PIL import Image, UnidentifiedImageError

from .importing.types import UploadRejected

Image.MAX_IMAGE_PIXELS = 25_000_000

JPEG_QUALITY = 86
_FILENAME_RE = re.compile(r"^[0-9a-f]{32}\.jpg$")


@dataclass(frozen=True)
class Encoded:
    data: bytes
    width: int
    height: int


def reencode(data: bytes, *, max_size: tuple[int, int], formats: set[str], label: str) -> Encoded:
    """Decode `data`, flatten it to RGB, shrink it to `max_size`, return it as a JPEG.

    Raises UploadRejected with a message that names the kind of picture (`label`).
    """
    try:
        with Image.open(BytesIO(data)) as image:
            if image.format not in formats:
                names = ", ".join(sorted(name.title() for name in formats))
                raise UploadRejected(f"A {label} must be one of: {names}.")
            image = image.convert("RGB")
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError):
        raise UploadRejected(f"That {label} couldn't be read.") from None

    image.thumbnail(max_size)
    buffer = BytesIO()
    image.save(buffer, "JPEG", quality=JPEG_QUALITY, optimize=True)
    return Encoded(buffer.getvalue(), image.width, image.height)


@contextmanager
def discard_new_files_on_failure():
    """Delete every picture saved inside this block if the block fails.

    Files are written before the database commit. If the commit (or anything after the
    save) fails, no database row points at them, so they would pile up unnoticed.
    """
    pending = g.setdefault("new_pictures", [])
    start = len(pending)
    try:
        yield
    except Exception:
        for store, name in pending[start:]:
            store.delete(name)
        raise
    finally:
        del pending[start:]


class PictureStore:
    """A folder of JPEGs named by random ids. The folder comes from app config."""

    def __init__(self, config_key: str):
        self.config_key = config_key

    def directory(self) -> Path:
        folder = Path(current_app.config[self.config_key])
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def save(self, jpeg: bytes) -> str:
        name = f"{uuid.uuid4().hex}.jpg"
        (self.directory() / name).write_bytes(jpeg)
        g.setdefault("new_pictures", []).append((self, name))
        return name

    def path(self, name: str | None) -> Path | None:
        """The file's path, or None if `name` isn't one of our generated names."""
        return self.directory() / name if name and _FILENAME_RE.match(name) else None

    def delete(self, name: str | None) -> None:
        path = self.path(name)
        if path and path.exists():
            path.unlink()
