"""Creating, editing and deleting books and chapters."""
from dataclasses import dataclass, field

from sqlalchemy import delete, update

from ..extensions import db
from ..models import GENRE, MOOD, Book, Chapter, Follow, Notification, ReadingProgress
from . import chapter_images, covers, image_tokens, notifier
from .pictures import discard_new_files_on_failure
from .importing import ParsedChapter
from .tagger import suggest_tags
from .text import clean_line, clean_text, count_words

TAGGING_SAMPLE_CHARS = 15_000


@dataclass
class BookDetails:
    title: str
    author: str
    description: str
    visibility: str
    status: str
    genres: list[str] = field(default_factory=list)
    moods: list[str] = field(default_factory=list)


def _apply_details(book: Book, details: BookDetails) -> None:
    book.title = clean_line(details.title, 200)
    book.author = clean_line(details.author, 120)
    book.description = clean_text(details.description)
    book.status = details.status
    book.set_tags(GENRE, details.genres)
    book.set_tags(MOOD, details.moods)
    _set_visibility(book, details.visibility)


def _set_visibility(book: Book, visibility: str) -> None:
    """Going private removes other readers' follows and notifications for the book."""
    if book.id and visibility == Book.PRIVATE and book.is_public:
        db.session.execute(
            delete(Follow).where(Follow.book_id == book.id, Follow.user_id != book.owner_id)
        )
        db.session.execute(
            delete(Notification).where(
                Notification.book_id == book.id, Notification.user_id != book.owner_id
            )
        )
    book.visibility = visibility


def _build_chapter(number: int, title: str, body: str) -> Chapter:
    text = clean_text(body)
    return Chapter(
        number=number,
        title=clean_line(title, 200) or f"Chapter {number}",
        body=text,
        word_count=count_words(image_tokens.strip(text)),
    )


def _append_chapters(book: Book, parsed: list[ParsedChapter], first_number: int) -> list[Chapter]:
    chapters = [
        _build_chapter(first_number + offset, item.title, item.body)
        for offset, item in enumerate(parsed)
    ]
    book.chapters.extend(chapters)
    return chapters


def _store_pictures(book: Book, chapters: list[Chapter], parsed: list[ParsedChapter]) -> None:
    """Save each chapter's pictures and point its text at them. The book must be saved first."""
    db.session.flush()
    for chapter, source in zip(chapters, parsed):
        if source.images:
            chapter.body = chapter_images.link_pictures(book, chapter.body, source.images)


def _auto_tag(book: Book, parsed: list[ParsedChapter]) -> None:
    """Fill in genre and mood from the text when the uploader chose none."""
    if book.genres or book.moods or not parsed:
        return
    sample = " ".join(chapter.body for chapter in parsed)[:TAGGING_SAMPLE_CHARS]
    genres, moods = suggest_tags(sample)
    book.set_tags(GENRE, genres)
    book.set_tags(MOOD, moods)


def create_book(owner, details: BookDetails, parsed: list[ParsedChapter], cover_file=None) -> Book:
    with discard_new_files_on_failure():
        cover_name = covers.save_cover(cover_file) if cover_file else None  # may raise first
        book = Book(owner=owner, cover_filename=cover_name)
        _apply_details(book, details)
        book.author = book.author or owner.username

        chapters = _append_chapters(book, parsed, first_number=1)
        book.refresh_stats()
        _auto_tag(book, parsed)

        db.session.add(book)
        _store_pictures(book, chapters, parsed)
        db.session.commit()
    return book


def update_book(book: Book, details: BookDetails, cover_file=None, remove_cover=False) -> None:
    _apply_details(book, details)
    book.author = book.author or book.owner.username

    old_cover = book.cover_filename
    with discard_new_files_on_failure():
        if cover_file:
            book.cover_filename = covers.save_cover(cover_file)
        elif remove_cover:
            book.cover_filename = None
        db.session.commit()

    if old_cover and old_cover != book.cover_filename:
        covers.delete_cover(old_cover)


def add_chapters(book: Book, parsed: list[ParsedChapter]) -> list[Chapter]:
    """Append one or many chapters and send followers a single notification."""
    with discard_new_files_on_failure():
        added = _append_chapters(book, parsed, first_number=book.chapter_count + 1)
        book.refresh_stats()
        _store_pictures(book, added, parsed)
        # Readers who had finished the book are back to "continue reading".
        db.session.execute(
            update(ReadingProgress)
            .where(ReadingProgress.book_id == book.id, ReadingProgress.finished.is_(True))
            .values(finished=False)
        )
        if book.is_public and added:
            notifier.notify_followers(book, added)
        db.session.commit()
    return added


def add_chapter(book: Book, title: str, body: str) -> Chapter:
    return add_chapters(book, [ParsedChapter(title, body)])[0]


def delete_book(book: Book) -> None:
    cover = book.cover_filename
    picture_files = [image.filename for image in book.images]
    db.session.delete(book)
    db.session.commit()
    covers.delete_cover(cover)
    for name in picture_files:
        chapter_images.store.delete(name)
