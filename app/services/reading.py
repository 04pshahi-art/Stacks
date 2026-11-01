"""Reading progress and following."""
from sqlalchemy import select

from ..extensions import db
from ..models import Book, Follow, ReadingProgress


def get_progress(user_id: int, book_id: int) -> ReadingProgress | None:
    return db.session.scalar(
        select(ReadingProgress).where(
            ReadingProgress.user_id == user_id, ReadingProgress.book_id == book_id
        )
    )


def is_following(user_id: int, book_id: int) -> bool:
    return db.session.scalar(
        select(Follow.id).where(Follow.user_id == user_id, Follow.book_id == book_id)
    ) is not None


def set_following(user_id: int, book: Book, follow: bool) -> None:
    existing = db.session.scalar(
        select(Follow).where(Follow.user_id == user_id, Follow.book_id == book.id)
    )
    if follow and not existing:
        db.session.add(Follow(user_id=user_id, book_id=book.id))
    elif not follow and existing:
        db.session.delete(existing)
    db.session.commit()


def start_reading(user, book: Book) -> ReadingProgress:
    """Return the reader's progress, creating it on first open.

    Readers of someone else's public book automatically follow it, so they
    hear about new chapters without having to find a button.
    """
    progress = get_progress(user.id, book.id)
    if progress is None:
        progress = ReadingProgress(user_id=user.id, book_id=book.id)
        db.session.add(progress)
        if book.is_public and not book.is_owned_by(user):
            db.session.add(Follow(user_id=user.id, book_id=book.id))
        db.session.commit()
    return progress


def save_progress(
    progress: ReadingProgress, book: Book, chapter_number: int, ratio: float, finished: bool
) -> None:
    progress.chapter_number = max(1, min(chapter_number, max(book.chapter_count, 1)))
    progress.ratio = max(0.0, min(1.0, ratio))
    # Finishing sticks: scrolling back through a finished book doesn't undo it.
    progress.finished = progress.finished or finished
    db.session.commit()
