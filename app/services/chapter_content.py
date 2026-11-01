"""A chapter as the reader shows it: paragraphs of text and pictures, in order."""
from flask import url_for
from sqlalchemy import select

from ..extensions import db
from ..models import Book, BookImage, Chapter
from . import image_tokens


def _pictures_by_id(book: Book, ids: set[int]) -> dict[int, BookImage]:
    """Only this book's own pictures, so a token can't show anyone else's."""
    if not ids:
        return {}
    rows = db.session.scalars(
        select(BookImage).where(BookImage.book_id == book.id, BookImage.id.in_(ids))
    )
    return {image.id: image for image in rows}


def blocks_for(book: Book, chapter: Chapter) -> list[dict]:
    paragraphs = chapter.paragraphs
    wanted = {image_id for p in paragraphs if (image_id := image_tokens.stored_id_of(p))}
    pictures = _pictures_by_id(book, wanted)

    blocks = []
    for paragraph in paragraphs:
        picture = pictures.get(image_tokens.stored_id_of(paragraph) or 0)
        if picture:
            blocks.append(
                {
                    "type": "image",
                    "url": url_for("books.image", book_id=book.id, image_id=picture.id),
                    "alt": picture.alt,
                    "width": picture.width,
                    "height": picture.height,
                }
            )
        else:
            blocks.append({"type": "text", "text": paragraph})
    return blocks
