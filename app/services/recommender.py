"""Reading-taste profile and book recommendations.

How it works, in plain terms:
  1. Every book the reader finished (or got at least halfway through) adds its
     genres and moods to their taste profile. Genres and moods picked when they
     signed up count too, a little less.
  2. After MIN_BOOKS_FOR_RECOMMENDATIONS books, picks are personal. Before that
     the profile still uses their chosen favourites.
  3. Each unread public book is scored by how well its tags match the profile.

The scoring is plain arithmetic, so it needs no model and runs instantly.
"""
import math
from dataclasses import dataclass, field

from flask import current_app
from sqlalchemy import func, select

from ..extensions import db
from ..models import GENRE, MOOD, Book, ReadingProgress, User
from .queries import public_books, readers_subquery

FINISHED_WEIGHT = 1.0
HALFWAY_WEIGHT = 0.5
STATED_PREFERENCE_WEIGHT = 0.75
HALFWAY_FRACTION = 0.5
GENRE_FACTOR = 1.0
MOOD_FACTOR = 0.7
POPULARITY_FACTOR = 0.05
CANDIDATE_POOL = 300


@dataclass
class Taste:
    genre_weights: dict[str, float] = field(default_factory=dict)
    mood_weights: dict[str, float] = field(default_factory=dict)
    books_read: int = 0
    books_needed: int = 3

    @property
    def unlocked(self) -> bool:
        return self.books_read >= self.books_needed

    @property
    def books_remaining(self) -> int:
        return max(0, self.books_needed - self.books_read)

    @property
    def has_signal(self) -> bool:
        return bool(self.genre_weights or self.mood_weights)

    def top(self, kind: str, limit: int = 5) -> list[tuple[str, float]]:
        """The strongest tags with their share of the total, from 0 to 1."""
        weights = self.genre_weights if kind == GENRE else self.mood_weights
        total = sum(weights.values()) or 1.0
        ranked = sorted(weights.items(), key=lambda item: item[1], reverse=True)
        return [(name, weight / total) for name, weight in ranked[:limit]]


@dataclass(frozen=True)
class Candidate:
    book_id: int
    genres: tuple[str, ...]
    moods: tuple[str, ...]
    readers: int = 0


@dataclass(frozen=True)
class Scored:
    book_id: int
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class Recommendation:
    book: Book
    reasons: tuple[str, ...]

    @property
    def reason_text(self) -> str:
        return ", ".join(self.reasons)


def _relative(weights: dict[str, float]) -> dict[str, float]:
    """Scale so the strongest tag is 1.0."""
    top = max(weights.values(), default=0.0)
    return {name: weight / top for name, weight in weights.items()} if top else {}


def rank(taste: Taste, candidates: list[Candidate], limit: int) -> list[Scored]:
    """Score candidates against a taste profile, best first. Pure, no database."""
    genre_share = _relative(taste.genre_weights)
    mood_share = _relative(taste.mood_weights)

    scored = []
    for candidate in candidates:
        matches = [
            (genre_share[g] * GENRE_FACTOR, g) for g in candidate.genres if g in genre_share
        ] + [(mood_share[m] * MOOD_FACTOR, m) for m in candidate.moods if m in mood_share]
        if not matches:
            continue
        score = sum(value for value, _ in matches)
        score += POPULARITY_FACTOR * math.log1p(candidate.readers)
        reasons = tuple(name for _, name in sorted(matches, reverse=True)[:2])
        scored.append(Scored(candidate.book_id, score, reasons))

    scored.sort(key=lambda item: (item.score, item.book_id), reverse=True)
    return scored[:limit]


# --- database glue -------------------------------------------------------
def _add_weight(weights: dict[str, float], names: list[str], amount: float) -> None:
    for name in names:
        weights[name] = weights.get(name, 0.0) + amount


def build_taste(user: User) -> Taste:
    taste = Taste(books_needed=current_app.config["MIN_BOOKS_FOR_RECOMMENDATIONS"])

    _add_weight(taste.genre_weights, user.preference_values(GENRE), STATED_PREFERENCE_WEIGHT)
    _add_weight(taste.mood_weights, user.preference_values(MOOD), STATED_PREFERENCE_WEIGHT)

    rows = db.session.execute(
        select(Book, ReadingProgress)
        .join(ReadingProgress, ReadingProgress.book_id == Book.id)
        .where(ReadingProgress.user_id == user.id)
    ).all()
    for book, progress in rows:
        if progress.finished:
            weight = FINISHED_WEIGHT
        elif progress.fraction(book.chapter_count) >= HALFWAY_FRACTION:
            weight = HALFWAY_WEIGHT
        else:
            continue
        taste.books_read += 1
        _add_weight(taste.genre_weights, book.genres, weight)
        _add_weight(taste.mood_weights, book.moods, weight)
    return taste


def _load_candidates(user: User) -> dict[int, tuple[Book, int]]:
    """Unread public books by other people, with how many readers each has."""
    started = select(ReadingProgress.book_id).where(ReadingProgress.user_id == user.id)
    readers = readers_subquery()
    stmt = (
        public_books()
        .add_columns(func.coalesce(readers.c.readers, 0))
        .outerjoin(readers, readers.c.book_id == Book.id)
        .where(Book.owner_id != user.id, Book.id.not_in(started))
        .order_by(Book.created_at.desc())
        .limit(CANDIDATE_POOL)
    )
    return {book.id: (book, count) for book, count in db.session.execute(stmt).all()}


def recommend(user: User, taste: Taste | None = None, limit: int = 8) -> list[Recommendation]:
    taste = taste or build_taste(user)
    if not taste.has_signal:
        return []

    loaded = _load_candidates(user)
    candidates = [
        Candidate(book.id, tuple(book.genres), tuple(book.moods), readers)
        for book, readers in loaded.values()
    ]
    return [
        Recommendation(loaded[item.book_id][0], item.reasons)
        for item in rank(taste, candidates, limit)
    ]
