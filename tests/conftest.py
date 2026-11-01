"""Fixtures. Tests that touch the database use a throw-away in-memory SQLite database."""
import pytest

PASSWORD = "Correct-Horse-42"


@pytest.fixture
def app(tmp_path):
    from app import create_app
    from app.config import TestConfig
    from app.extensions import db

    settings = {
        "WTF_CSRF_ENABLED": False,
        "UPLOAD_DIR": tmp_path / "covers",
        "IMAGE_DIR": tmp_path / "images",
    }
    app = create_app(type("Config", (TestConfig,), settings))
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_user(app):
    """Create an account directly. Returns the user."""
    from app.services import accounts

    def make(name="reader"):
        return accounts.register_user(name, f"{name}@example.com", PASSWORD)

    return make


@pytest.fixture
def sign_in(app):
    """Return a test client that is signed in as the given user name."""

    def sign(name):
        browser = app.test_client()
        response = browser.post("/login", data={"identifier": name, "password": PASSWORD})
        assert response.status_code == 302, "sign-in failed"
        return browser

    return sign


@pytest.fixture
def make_book(app):
    """Create a book with chapters (and optional pictures) for `owner`."""
    from app.models import Book
    from app.services import publishing
    from app.services.importing import ParsedChapter

    def make(owner, visibility=Book.PRIVATE, chapters=None, title="A Book"):
        details = publishing.BookDetails(
            title=title, author="", description="", visibility=visibility, status=Book.COMPLETE
        )
        parsed = chapters or [ParsedChapter("One", "First chapter text. " * 30)]
        return publishing.create_book(owner, details, parsed)

    return make
