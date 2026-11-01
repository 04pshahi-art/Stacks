"""If saving to the database fails, picture files written just before must not be left behind."""
import pytest
from helpers import jpeg_bytes
from werkzeug.datastructures import FileStorage
from io import BytesIO

from app.extensions import db
from app.models import Book
from app.services import publishing
from app.services.importing import ParsedChapter, ParsedImage


def details():
    return publishing.BookDetails(title="T", author="", description="", visibility=Book.PRIVATE, status=Book.COMPLETE)


def failing_commit(monkeypatch):
    def boom():
        raise RuntimeError("database went away")

    monkeypatch.setattr(db.session, "commit", boom)


def files_in(app):
    return [path for key in ("UPLOAD_DIR", "IMAGE_DIR") if app.config[key].exists() for path in app.config[key].iterdir()]


def test_failed_create_removes_cover_and_chapter_pictures(app, make_user, monkeypatch):
    owner = make_user("owner")
    chapter = ParsedChapter("One", "[[img:i1]]\n\n" + "words " * 40, {"i1": ParsedImage(jpeg_bytes(), "")})
    cover = FileStorage(BytesIO(jpeg_bytes()), filename="cover.jpg")
    failing_commit(monkeypatch)

    with pytest.raises(RuntimeError):
        publishing.create_book(owner, details(), [chapter], cover)
    assert files_in(app) == []


def test_failed_add_chapters_removes_new_pictures_but_keeps_old_ones(app, make_user, make_book, monkeypatch):
    owner = make_user("owner")
    old = ParsedChapter("One", "[[img:i1]]\n\n" + "words " * 40, {"i1": ParsedImage(jpeg_bytes(), "")})
    book = make_book(owner, chapters=[old])
    before = files_in(app)
    assert len(before) == 1

    new = ParsedChapter("Two", "[[img:i1]]\n\n" + "words " * 40, {"i1": ParsedImage(jpeg_bytes((50, 50)), "")})
    failing_commit(monkeypatch)
    with pytest.raises(RuntimeError):
        publishing.add_chapters(book, [new])
    assert files_in(app) == before


def test_failed_cover_change_removes_the_new_cover(app, make_user, make_book, monkeypatch):
    book = make_book(make_user("owner"))
    cover = FileStorage(BytesIO(jpeg_bytes()), filename="cover.jpg")
    failing_commit(monkeypatch)
    with pytest.raises(RuntimeError):
        publishing.update_book(book, details(), cover)
    assert files_in(app) == []


def test_successful_saves_keep_their_files(app, make_user):
    chapter = ParsedChapter("One", "[[img:i1]]\n\n" + "words " * 40, {"i1": ParsedImage(jpeg_bytes(), "")})
    publishing.create_book(make_user("owner"), details(), [chapter])
    assert len(files_in(app)) == 1
