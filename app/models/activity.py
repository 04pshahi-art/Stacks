from ..extensions import db
from .base import table_args, utcnow


class ReadingProgress(db.Model):
    """Where one reader is in one book. Also the signal behind recommendations."""

    __tablename__ = "reading_progress"
    __table_args__ = table_args(db.UniqueConstraint("user_id", "book_id"))

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    book_id = db.Column(
        db.Integer, db.ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chapter_number = db.Column(db.Integer, nullable=False, default=1)
    ratio = db.Column(db.Float, nullable=False, default=0.0)  # 0-1 inside the chapter
    finished = db.Column(db.Boolean, nullable=False, default=False)
    started_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    book = db.relationship("Book")

    def fraction(self, chapter_count: int) -> float:
        """How far through the whole book, from 0 to 1."""
        if self.finished:
            return 1.0
        done = (self.chapter_number - 1) + self.ratio
        return max(0.0, min(1.0, done / max(chapter_count, 1)))


class Follow(db.Model):
    """A reader who wants to hear about new chapters of a book."""

    __tablename__ = "follows"
    __table_args__ = table_args(db.UniqueConstraint("user_id", "book_id"))

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    book_id = db.Column(
        db.Integer, db.ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class Notification(db.Model):
    __tablename__ = "notifications"
    __table_args__ = table_args(db.Index("ix_notifications_user_unread", "user_id", "is_read"))

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    book_id = db.Column(db.Integer, db.ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    chapter_number = db.Column(db.Integer, nullable=False)
    message = db.Column(db.String(300), nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
