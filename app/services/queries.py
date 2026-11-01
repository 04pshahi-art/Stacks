"""Read-only book queries shared by pages, the recommender and the chatbot."""
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import GENRE, MOOD, Book, BookTag, ReadingProgress
from ..security import escape_like

SORT_OPTIONS = {
    "newest": "Newest",
    "popular": "Most read",
    "title": "Title A to Z",
}
MAX_QUERY_LENGTH = 100


def readers_subquery():
    """How many people have started each book."""
    return (
        select(ReadingProgress.book_id, func.count().label("readers"))
        .group_by(ReadingProgress.book_id)
        .subquery()
    )


def public_books():
    """Public books that have at least one chapter to read."""
    return select(Book).where(Book.visibility == Book.PUBLIC, Book.chapter_count > 0)


def readable_by(user_id: int):
    """SQL condition: public books, plus the user's own."""
    return or_(Book.visibility == Book.PUBLIC, Book.owner_id == user_id)


def _has_tag(kind: str, value: str):
    return Book.tags.any(and_(BookTag.kind == kind, BookTag.value == value))


def _apply_sort(stmt, sort: str):
    if sort == "popular":
        readers = readers_subquery()
        return stmt.outerjoin(readers, readers.c.book_id == Book.id).order_by(
            func.coalesce(readers.c.readers, 0).desc(), Book.id.desc()
        )
    if sort == "title":
        return stmt.order_by(Book.title.asc())
    return stmt.order_by(Book.created_at.desc(), Book.id.desc())


def search_books(
    *,
    text: str = "",
    genre: str = "",
    mood: str = "",
    sort: str = "newest",
    page: int = 1,
    per_page: int = 24,
):
    """Search public books by text, genre and mood. Returns a Flask-SQLAlchemy page."""
    stmt = public_books().options(joinedload(Book.owner))

    text = text.strip()[:MAX_QUERY_LENGTH]
    if text:
        pattern = f"%{escape_like(text)}%"
        stmt = stmt.where(
            or_(
                Book.title.ilike(pattern, escape="\\"),
                Book.author.ilike(pattern, escape="\\"),
                Book.description.ilike(pattern, escape="\\"),
            )
        )
    if genre:
        stmt = stmt.where(_has_tag(GENRE, genre))
    if mood:
        stmt = stmt.where(_has_tag(MOOD, mood))

    stmt = _apply_sort(stmt, sort if sort in SORT_OPTIONS else "newest")
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)


def find_books_by_tags(genres: list[str], moods: list[str], limit: int = 5) -> list[Book]:
    """Public books matching any of the given genres or moods."""
    conditions = [_has_tag(GENRE, g) for g in genres] + [_has_tag(MOOD, m) for m in moods]
    if not conditions:
        return []
    stmt = public_books().where(or_(*conditions)).order_by(Book.id.desc()).limit(limit)
    return list(db.session.scalars(stmt))


def latest_public(limit: int = 12) -> list[Book]:
    stmt = public_books().options(joinedload(Book.owner)).order_by(Book.created_at.desc()).limit(limit)
    return list(db.session.scalars(stmt))


def popular_public(limit: int = 12) -> list[Book]:
    stmt = _apply_sort(public_books(), "popular").limit(limit)
    return list(db.session.scalars(stmt))


def _progress_rows(user_id: int, finished: bool, limit: int | None):
    stmt = (
        select(Book, ReadingProgress)
        .join(ReadingProgress, ReadingProgress.book_id == Book.id)
        .where(
            ReadingProgress.user_id == user_id,
            ReadingProgress.finished.is_(finished),
            readable_by(user_id),  # a book made private since is no longer listed
        )
        .order_by(ReadingProgress.updated_at.desc())
    )
    if limit:
        stmt = stmt.limit(limit)
    return db.session.execute(stmt).all()


def continue_reading(user_id: int, limit: int | None = 8):
    """(Book, ReadingProgress) rows for books the reader hasn't finished."""
    return _progress_rows(user_id, finished=False, limit=limit)


def finished_books(user_id: int, limit: int | None = None):
    return _progress_rows(user_id, finished=True, limit=limit)


def uploaded_books(user_id: int) -> list[Book]:
    stmt = select(Book).where(Book.owner_id == user_id).order_by(Book.updated_at.desc())
    return list(db.session.scalars(stmt))
