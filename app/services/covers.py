"""Cover images (see pictures.py for how every picture is made safe)."""
from pathlib import Path

from flask import current_app

from .importing.types import UploadRejected
from .pictures import PictureStore, reencode

store = PictureStore("UPLOAD_DIR")

COVER_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_SIZE = (600, 900)


def cover_path(name: str) -> Path | None:
    return store.path(name)


def save_cover(file_storage) -> str:
    """Validate and store an uploaded image. Returns the new file name."""
    limit = current_app.config["MAX_COVER_BYTES"]
    data = file_storage.read(limit + 1)
    if len(data) > limit:
        raise UploadRejected("Cover images must be under 2 MB.")
    encoded = reencode(data, max_size=MAX_SIZE, formats=COVER_FORMATS, label="cover image")
    return store.save(encoded.data)


def delete_cover(name: str | None) -> None:
    store.delete(name)
