from datetime import timedelta

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from .base import table_args, utcnow


class User(UserMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = table_args()

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    # Bumped on password change so every older session stops working.
    auth_version = db.Column(db.Integer, nullable=False, default=1)
    failed_logins = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime)
    onboarded = db.Column(db.Boolean, nullable=False, default=False)

    preferences = db.relationship(
        "UserPreference", back_populates="user", cascade="all, delete-orphan"
    )
    books = db.relationship("Book", back_populates="owner", cascade="all, delete-orphan")

    # --- passwords -------------------------------------------------------
    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)  # scrypt

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    # --- lockout ---------------------------------------------------------
    def is_locked(self) -> bool:
        return self.locked_until is not None and self.locked_until > utcnow()

    def register_failure(self, max_failures: int, lockout_minutes: int) -> None:
        self.failed_logins += 1
        if self.failed_logins >= max_failures:
            self.locked_until = utcnow() + timedelta(minutes=lockout_minutes)
            self.failed_logins = 0

    def clear_failures(self) -> None:
        self.failed_logins = 0
        self.locked_until = None

    # --- Flask-Login -----------------------------------------------------
    def get_id(self) -> str:
        return f"{self.id}:{self.auth_version}"

    # --- preferences -----------------------------------------------------
    def preference_values(self, kind: str) -> list[str]:
        return [p.value for p in self.preferences if p.kind == kind]

    def set_preferences(self, kind: str, values: list[str]) -> None:
        kept = [p for p in self.preferences if p.kind != kind]
        fresh = [UserPreference(kind=kind, value=value) for value in dict.fromkeys(values)]
        self.preferences = kept + fresh


class UserPreference(db.Model):
    """A genre or mood the reader said they enjoy."""

    __tablename__ = "user_preferences"
    __table_args__ = table_args(db.UniqueConstraint("user_id", "kind", "value"))

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind = db.Column(db.String(10), nullable=False)
    value = db.Column(db.String(40), nullable=False)

    user = db.relationship("User", back_populates="preferences")
