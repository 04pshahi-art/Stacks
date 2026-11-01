"""Registration, sign-in and password changes."""
from flask import current_app
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models import User

# Checked when the account doesn't exist so response time doesn't reveal it.
_TIMING_EQUALISER_HASH = generate_password_hash("folio-timing-equaliser")


class AccountExists(Exception):
    """The username or email is already registered."""


def normalise_email(email: str) -> str:
    return email.strip().lower()


def load_user(session_id: str) -> User | None:
    """Flask-Login loader. Sessions carry 'id:auth_version'; stale ones are rejected."""
    try:
        raw_id, raw_version = session_id.split(":", 1)
        user = db.session.get(User, int(raw_id))
        return user if user and user.auth_version == int(raw_version) else None
    except (ValueError, AttributeError):
        return None


def find_by_identifier(identifier: str) -> User | None:
    lowered = identifier.strip().lower()
    return db.session.scalar(
        select(User).where(or_(func.lower(User.username) == lowered, User.email == lowered))
    )


def conflicting_field(username: str, email: str) -> str | None:
    """Return 'username' or 'email' if either is already taken."""
    if db.session.scalar(select(User.id).where(func.lower(User.username) == username.lower())):
        return "username"
    if db.session.scalar(select(User.id).where(User.email == normalise_email(email))):
        return "email"
    return None


def register_user(username: str, email: str, password: str) -> User:
    if conflicting_field(username, email):
        raise AccountExists
    user = User(username=username, email=normalise_email(email))
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:  # two sign-ups raced past the check above
        db.session.rollback()
        raise AccountExists from None
    return user


def authenticate(identifier: str, password: str) -> User | None:
    """Return the user for valid credentials, otherwise None.

    Repeated failures lock the account for a while. A locked account is never
    checked against the password, and the caller shows one generic message for
    every failure so nothing reveals which accounts exist.
    """
    user = find_by_identifier(identifier)
    if user is None:
        check_password_hash(_TIMING_EQUALISER_HASH, password)
        return None
    if user.is_locked():
        return None

    if user.check_password(password):
        user.clear_failures()
        db.session.commit()
        return user

    user.register_failure(
        current_app.config["LOGIN_MAX_FAILURES"],
        current_app.config["LOGIN_LOCKOUT_MINUTES"],
    )
    db.session.commit()
    return None


def change_password(user: User, current_password: str, new_password: str) -> bool:
    """Set a new password and sign out every other session."""
    if not user.check_password(current_password):
        return False
    user.set_password(new_password)
    user.auth_version += 1
    db.session.commit()
    return True
