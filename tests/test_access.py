"""Private books stay private, and only owners can change their books."""
import pytest
from helpers import jpeg_bytes

from app.models import Book
from app.services.importing import ParsedChapter, ParsedImage


def book_with_picture(make_book, owner, visibility):
    chapter = ParsedChapter("One", "[[img:i1]]\n\n" + "Some words here. " * 30, {"i1": ParsedImage(jpeg_bytes(), "A map")})
    book = make_book(owner, visibility, [chapter])
    return book, book.images[0].id


READ_PATHS = [
    "/books/{book}",
    "/read/{book}",
    "/api/books/{book}/toc",
    "/api/books/{book}/chapters/1",
    "/books/{book}/images/{image}",
]


@pytest.mark.parametrize("path", READ_PATHS)
def test_private_book_is_visible_only_to_its_owner(path, app, make_user, make_book, sign_in):
    owner, other = make_user("owner"), make_user("other")
    book, image = book_with_picture(make_book, owner, Book.PRIVATE)
    url = path.format(book=book.id, image=image)

    assert sign_in("owner").get(url).status_code == 200
    assert sign_in("other").get(url).status_code == 404  # looks like it doesn't exist


def test_private_book_page_is_hidden_from_visitors_not_signed_in(client, make_user, make_book):
    book = make_book(make_user("owner"), Book.PRIVATE)
    assert client.get(f"/books/{book.id}").status_code == 404


@pytest.mark.parametrize("path", READ_PATHS)
def test_public_book_can_be_read_by_other_signed_in_users(path, make_user, make_book, sign_in):
    owner, other = make_user("owner"), make_user("other")
    book, image = book_with_picture(make_book, owner, Book.PUBLIC)
    assert sign_in("other").get(path.format(book=book.id, image=image)).status_code == 200


def test_a_picture_cannot_be_fetched_through_a_different_book(make_user, make_book, sign_in):
    owner = make_user("owner")
    _, image = book_with_picture(make_book, owner, Book.PRIVATE)
    other_book = make_book(owner, Book.PRIVATE)
    assert sign_in("owner").get(f"/books/{other_book.id}/images/{image}").status_code == 404


def test_pictures_need_an_account_even_for_public_books(client, make_user, make_book):
    book, image = book_with_picture(make_book, make_user("owner"), Book.PUBLIC)
    assert client.get(f"/books/{book.id}/images/{image}").status_code == 302


def test_other_people_cannot_edit_or_delete_a_public_book(make_user, make_book, sign_in):
    book = make_book(make_user("owner"), Book.PUBLIC)
    make_user("other")
    other = sign_in("other")
    assert other.get(f"/books/{book.id}/edit").status_code == 403
    assert other.post(f"/books/{book.id}/delete").status_code == 403
    assert other.get(f"/books/{book.id}/chapters/new").status_code == 403
    assert other.post(f"/books/{book.id}/chapters/import").status_code == 403


def test_reading_progress_cannot_be_saved_on_a_private_book_you_cannot_read(make_user, make_book, sign_in):
    book = make_book(make_user("owner"), Book.PRIVATE)
    make_user("other")
    response = sign_in("other").post(f"/api/books/{book.id}/progress", json={"chapter_number": 1, "ratio": 0.5})
    assert response.status_code == 404


def test_deleting_a_book_removes_its_picture_files(app, make_user, make_book, sign_in):
    owner = make_user("owner")
    book, _ = book_with_picture(make_book, owner, Book.PRIVATE)
    folder = app.config["IMAGE_DIR"]
    assert len(list(folder.iterdir())) == 1

    assert sign_in("owner").post(f"/books/{book.id}/delete").status_code == 302
    assert list(folder.iterdir()) == []
