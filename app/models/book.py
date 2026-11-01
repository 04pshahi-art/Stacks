import zlib

from ..extensions import db
from ..services.text import split_paragraphs
from .base import LongText, table_args, utcnow

GENRE = "genre"
MOOD = "mood"


class Book(db.Model):
    __tablename__ = "books"
    __table_args__ = table_args()

    PUBLIC = "public"
    PRIVATE = "private"
    ONGOING = "ongoing"
    COMPLETE = "complete"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    visibility = db.Column(db.String(10), nullable=False, default=PRIVATE, index=True)
    status = db.Column(db.String(10), nullable=False, default=COMPLETE)
    cover_filename = db.Column(db.String(40))

    # Denormalised so shelves don't need to count chapters per book.
    chapter_count = db.Column(db.Integer, nullable=False, default=0)
    word_count = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    owner = db.relationship("User", back_populates="books")
    chapters = db.relationship(
        "Chapter",
        back_populates="book",
        order_by="Chapter.number",
        cascade="all, delete-orphan",
    )
    tags = db.relationship(
        "BookTag", back_populates="book", cascade="all, delete-orphan", lazy="selectin"
    )
    images = db.relationship("BookImage", back_populates="book", cascade="all, delete-orphan")

    # --- access ----------------------------------------------------------
    @property
    def is_public(self) -> bool:
        return self.visibility == self.PUBLIC

    def is_owned_by(self, user) -> bool:
        return user.is_authenticated and user.id == self.owner_id

    def can_be_read_by(self, user) -> bool:
        return self.is_public or self.is_owned_by(user)

    # --- tags ------------------------------------------------------------
    def tag_values(self, kind: str) -> list[str]:
        return [tag.value for tag in self.tags if tag.kind == kind]

    @property
    def genres(self) -> list[str]:
        return self.tag_values(GENRE)

    @property
    def moods(self) -> list[str]:
        return self.tag_values(MOOD)

    def set_tags(self, kind: str, values: list[str]) -> None:
        kept = [tag for tag in self.tags if tag.kind != kind]
        fresh = [BookTag(kind=kind, value=value) for value in dict.fromkeys(values)]
        self.tags = kept + fresh

    # --- presentation helpers (cover colour carries the mood) -------------
    @property
    def mood_slug(self) -> str:
        moods = self.moods
        return moods[0].lower() if moods else "plain"

    @property
    def cover_variant(self) -> int:
        """Stable 0-3 value so every title gets its own spine width and height."""
        return zlib.crc32(self.title.encode("utf-8")) % 4

    def refresh_stats(self) -> None:
        self.chapter_count = len(self.chapters)
        self.word_count = sum(chapter.word_count for chapter in self.chapters)


class BookTag(db.Model):
    __tablename__ = "book_tags"
    __table_args__ = table_args(db.UniqueConstraint("book_id", "kind", "value"))

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(
        db.Integer, db.ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind = db.Column(db.String(10), nullable=False)
    value = db.Column(db.String(40), nullable=False, index=True)

    book = db.relationship("Book", back_populates="tags")


class Chapter(db.Model):
    __tablename__ = "chapters"
    __table_args__ = table_args(db.UniqueConstraint("book_id", "number"))

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(
        db.Integer, db.ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    # Plain text only. It is never rendered as HTML anywhere, which rules out XSS.
    body = db.deferred(db.Column(LongText, nullable=False))
    word_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    book = db.relationship("Book", back_populates="chapters")

    @property
    def paragraphs(self) -> list[str]:
        return split_paragraphs(self.body)


class BookImage(db.Model):
    """A picture inside a book. Chapters point at it with an [[img:ID]] line."""

    __tablename__ = "book_images"
    __table_args__ = table_args()

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(
        db.Integer, db.ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename = db.Column(db.String(40), nullable=False)
    alt = db.Column(db.String(300), nullable=False, default="")
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)

    book = db.relationship("Book", back_populates="images")
