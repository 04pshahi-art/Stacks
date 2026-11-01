"""Tell followers when a publisher adds a chapter."""
from sqlalchemy import select

from ..extensions import db
from ..models import Book, Chapter, Follow, Notification


def _message(book: Book, chapters: list[Chapter]) -> str:
    first = chapters[0]
    if len(chapters) == 1:
        return f"New chapter in “{book.title}”: {first.title}"[:300]
    return f"{len(chapters)} new chapters in “{book.title}”, starting with: {first.title}"[:300]


def notify_followers(book: Book, chapters: list[Chapter]) -> int:
    """Queue one notification per follower (not the publisher), however many chapters
    were published at once. Returns the count."""
    follower_ids = db.session.scalars(
        select(Follow.user_id).where(Follow.book_id == book.id, Follow.user_id != book.owner_id)
    ).all()

    message = _message(book, chapters)
    db.session.add_all(
        Notification(
            user_id=user_id,
            book_id=book.id,
            chapter_number=chapters[0].number,
            message=message,
        )
        for user_id in follower_ids
    )
    return len(follower_ids)
