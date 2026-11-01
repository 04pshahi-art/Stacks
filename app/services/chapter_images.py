"""Saving the pictures that come with a book."""
from ..extensions import db
from ..models import Book, BookImage
from . import image_tokens
from .importing.types import ParsedImage, UploadRejected
from .pictures import PictureStore, reencode
from .text import clean_line, clean_text

store = PictureStore("IMAGE_DIR")

PICTURE_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}
MAX_SIZE = (1600, 1600)
MAX_PICTURES_PER_BOOK = 300


def _save_one(book: Book, picture: ParsedImage) -> BookImage | None:
    """Re-encode and store one picture. A bad picture is skipped, not fatal."""
    if len(book.images) >= MAX_PICTURES_PER_BOOK:
        return None
    try:
        encoded = reencode(picture.data, max_size=MAX_SIZE, formats=PICTURE_FORMATS, label="picture")
    except UploadRejected:
        return None

    asset = BookImage(
        filename=store.save(encoded.data),
        alt=clean_line(picture.alt, 300),
        width=encoded.width,
        height=encoded.height,
    )
    book.images.append(asset)
    return asset


def link_pictures(book: Book, body: str, pictures: dict[str, ParsedImage]) -> str:
    """Store a chapter's pictures and turn its [[img:KEY]] lines into [[img:ID]] lines.

    Lines whose picture couldn't be stored are removed. The book must already be saved.
    """
    saved = {key: _save_one(book, picture) for key, picture in pictures.items()}
    db.session.flush()  # gives every new picture its id

    def new_key(key: str) -> str | None:
        if key not in saved:
            return key  # not ours: leave the text exactly as the author wrote it
        return str(saved[key].id) if saved[key] else None

    return clean_text(image_tokens.replace(body, new_key))
