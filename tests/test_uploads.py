"""Uploading books through the web form: limits and damaged files."""
import io

import pytest
from conftest import PASSWORD  # noqa: F401  (fixtures use it)
from helpers import jpeg_bytes, make_pdf, zip_bytes

from app.models import Book
from app.extensions import db


def upload(browser, filename, data, **extra):
    form = {"title": "Uploaded", "visibility": "private", "status": "complete",
            "file": (io.BytesIO(data), filename), **extra}
    return browser.post("/books/upload", data=form, content_type="multipart/form-data")


def book_count() -> int:
    return db.session.query(Book).count()


@pytest.fixture
def reader(make_user, sign_in):
    make_user("reader")
    return sign_in("reader")


def test_a_good_text_file_becomes_a_book(reader):
    response = upload(reader, "story.txt", ("Chapter 1\n\n" + "word " * 80).encode())
    assert response.status_code == 302 and book_count() == 1


@pytest.mark.parametrize("filename, data", [
    ("broken.pdf", b"%PDF-1.4 this is not really a pdf"),
    ("broken.epub", b"PK-not-a-real-epub"),
    ("broken.zip", b"definitely not a zip"),
    ("empty.txt", b""),
])
def test_damaged_files_are_refused_without_creating_a_book(reader, filename, data):
    response = upload(reader, filename, data)
    assert response.status_code == 200 and book_count() == 0


def test_files_of_the_wrong_type_are_refused(reader):
    response = upload(reader, "program.exe", b"MZ" + b"0" * 100)
    assert response.status_code == 200 and book_count() == 0


def test_a_pdf_with_too_much_text_is_refused(reader, monkeypatch):
    monkeypatch.setattr("app.services.importing.pdf.MAX_TOTAL_CHARS", 300)
    response = upload(reader, "huge.pdf", make_pdf(["word " * 60] * 10))
    assert response.status_code == 200 and book_count() == 0


def test_files_over_the_size_limit_are_refused(app, reader):
    app.config["MAX_CONTENT_LENGTH"] = 2000
    response = upload(reader, "big.txt", b"word " * 2000)
    assert response.status_code == 413 and book_count() == 0


def test_a_bad_cover_image_is_refused(reader):
    response = upload(reader, "story.txt", ("Chapter 1\n\n" + "word " * 80).encode(),
                      cover=(io.BytesIO(b"<svg onload=alert(1)>"), "cover.png"))
    assert response.status_code == 200 and book_count() == 0


def test_a_zip_book_keeps_its_pictures_only_as_safe_jpegs(app, reader):
    archive = zip_bytes({"story.md": "# One\n\n" + "word " * 80 + "\n\n![Map](map.jpg)\n", "map.jpg": jpeg_bytes()})
    assert upload(reader, "story.zip", archive).status_code == 302
    files = list(app.config["IMAGE_DIR"].iterdir())
    assert len(files) == 1 and files[0].read_bytes()[:3] == b"\xff\xd8\xff"


def test_adding_many_chapters_to_someone_elses_book_is_not_allowed(make_user, make_book, sign_in):
    book = make_book(make_user("owner"), Book.PRIVATE)
    make_user("other")
    response = sign_in("other").post(
        f"/books/{book.id}/chapters/import",
        data={"file": (io.BytesIO(b"Chapter 1\n\n" + b"word " * 80), "more.txt")},
        content_type="multipart/form-data",
    )
    assert response.status_code in (403, 404)
