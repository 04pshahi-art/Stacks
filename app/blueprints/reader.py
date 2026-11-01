import math

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from ..extensions import db, limiter
from ..models import Chapter
from ..services import chapter_content, reading
from .access import readable_book_or_404

bp = Blueprint("reader", __name__)


def _chapter_or_404(book, number: int) -> Chapter:
    chapter = db.session.scalar(
        select(Chapter).where(Chapter.book_id == book.id, Chapter.number == number)
    )
    if chapter is None:
        abort(404)
    return chapter


def _parse_progress(payload) -> tuple[int, float, bool] | None:
    """Validate the browser's progress report. Returns None if anything is off."""
    if not isinstance(payload, dict):
        return None
    chapter, ratio, finished = (
        payload.get("chapter_number"),
        payload.get("ratio"),
        payload.get("finished", False),
    )
    valid = (
        isinstance(chapter, int)
        and not isinstance(chapter, bool)
        and isinstance(ratio, (int, float))
        and not isinstance(ratio, bool)
        and math.isfinite(ratio)
        and isinstance(finished, bool)
    )
    return (chapter, float(ratio), finished) if valid else None


@bp.get("/read/<int:book_id>")
@login_required
def read(book_id):
    book = readable_book_or_404(book_id)
    if book.chapter_count == 0:
        flash("This book has no chapters yet.", "info")
        return redirect(url_for("books.detail", book_id=book.id))

    progress = reading.start_reading(current_user, book)
    start_chapter, start_ratio = progress.chapter_number, progress.ratio

    requested = request.args.get("chapter", type=int)  # e.g. from a notification
    if requested and 1 <= requested <= book.chapter_count:
        start_chapter, start_ratio = requested, 0.0
    return render_template(
        "reader/read.html", book=book, start_chapter=start_chapter, start_ratio=start_ratio
    )


@bp.get("/api/books/<int:book_id>/toc")
@login_required
def toc(book_id):
    book = readable_book_or_404(book_id)
    return jsonify(
        chapters=[
            {"number": c.number, "title": c.title, "words": c.word_count} for c in book.chapters
        ]
    )


@bp.get("/api/books/<int:book_id>/chapters/<int:number>")
@login_required
def chapter(book_id, number):
    book = readable_book_or_404(book_id)
    found = _chapter_or_404(book, number)
    return jsonify(
        number=found.number,
        title=found.title,
        blocks=chapter_content.blocks_for(book, found),
        total=book.chapter_count,
    )


@bp.post("/api/books/<int:book_id>/progress")
@login_required
@limiter.limit("60 per minute")
def save_progress(book_id):
    book = readable_book_or_404(book_id)
    parsed = _parse_progress(request.get_json(silent=True))
    if parsed is None:
        return jsonify(error="Invalid progress."), 400

    progress = reading.start_reading(current_user, book)
    reading.save_progress(progress, book, *parsed)
    return jsonify(ok=True)
