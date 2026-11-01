"""One place that decides who may see or change a book."""
from flask import abort
from flask_login import current_user

from ..extensions import db
from ..models import Book


def readable_book_or_404(book_id: int) -> Book:
    """A book the current user may read. Hidden books look like they don't exist."""
    book = db.session.get(Book, book_id)
    if book is None or not book.can_be_read_by(current_user):
        abort(404)
    return book


def owned_book_or_404(book_id: int) -> Book:
    """A book the current user owns. Other people's public books give 403."""
    book = readable_book_or_404(book_id)
    if not book.is_owned_by(current_user):
        abort(403)
    return book
