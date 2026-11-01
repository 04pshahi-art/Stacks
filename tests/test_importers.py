"""Uploaded files: what is accepted, and what is refused."""
import pytest
from helpers import jpeg_bytes, make_epub, make_pdf, zip_bytes

from app.services.importing import UploadRejected, parse_upload
from app.services.importing import types as import_types


def words(n=80):
    return " ".join(["word"] * n)


def test_plain_text_is_split_at_chapter_headings():
    text = f"Chapter 1\n\n{words()}\n\nChapter 2\n\n{words()}"
    assert len(parse_upload("book.txt", text.encode()).chapters) == 2


def test_unknown_extension_empty_and_garbage_files_are_refused():
    with pytest.raises(UploadRejected):
        parse_upload("virus.exe", b"MZ")
    with pytest.raises(UploadRejected):
        parse_upload("book.txt", b"")
    with pytest.raises(UploadRejected):
        parse_upload("book.pdf", b"not a pdf at all")
    with pytest.raises(UploadRejected):
        parse_upload("book.epub", b"not a zip")
    with pytest.raises(UploadRejected):
        parse_upload("book.zip", b"not a zip")


def test_pdf_text_is_extracted():
    parsed = parse_upload("book.pdf", make_pdf([words(60)] * 2))
    assert parsed.chapters and "word" in parsed.chapters[0].body


def test_pdf_with_too_much_text_is_refused_while_reading(monkeypatch):
    monkeypatch.setattr("app.services.importing.pdf.MAX_TOTAL_CHARS", 500)
    with pytest.raises(UploadRejected, match="too much text"):
        parse_upload("big.pdf", make_pdf([words(60)] * 20))


def test_every_format_obeys_the_overall_text_limit(monkeypatch):
    monkeypatch.setattr(import_types, "MAX_TOTAL_CHARS", 200)
    monkeypatch.setattr("app.services.importing.MAX_TOTAL_CHARS", 200)
    with pytest.raises(UploadRejected, match="too much text"):
        parse_upload("book.txt", words(500).encode())


def test_epub_chapters_and_pictures_are_imported():
    epub = make_epub(
        [("One", f"<p>{words()}</p><p><img src=\"pic.jpg\" alt=\"A map\"/></p>")],
        images={"pic.jpg": jpeg_bytes()},
    )
    chapter = parse_upload("book.epub", epub).chapters[0]
    assert "[[img:" in chapter.body
    assert len(chapter.images) == 1 and next(iter(chapter.images.values())).alt == "A map"


def test_zip_book_imports_markdown_with_its_pictures():
    archive = zip_bytes({
        "story.md": f"# Chapter 1\n\n{words()}\n\n![Harbour](images/harbour.jpg)\n",
        "images/harbour.jpg": jpeg_bytes(),
    })
    chapter = parse_upload("story.zip", archive).chapters[0]
    assert len(chapter.images) == 1


def test_zip_cannot_reach_files_outside_itself():
    archive = zip_bytes({"story.md": f"# One\n\n{words()}\n\n![x](../../secret.png)\n"})
    assert not parse_upload("story.zip", archive).chapters[0].images


def test_zip_without_markdown_is_refused():
    with pytest.raises(UploadRejected):
        parse_upload("story.zip", zip_bytes({"notes.bin": b"data"}))


def test_non_picture_files_are_not_imported_as_pictures():
    archive = zip_bytes({
        "story.md": f"# One\n\n{words()}\n\n![x](evil.svg)\n",
        "evil.svg": "<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>",
    })
    assert not parse_upload("story.zip", archive).chapters[0].images
