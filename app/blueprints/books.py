from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required

from ..extensions import db, limiter
from ..forms import ChapterFileForm, ChapterForm, EditBookForm, UploadBookForm
from ..models import BookImage
from ..services import chapter_images, covers, publishing, reading
from ..services.importing import UploadRejected, parse_upload
from ..services.tagger import suggest_tags
from .access import owned_book_or_404, readable_book_or_404

bp = Blueprint("books", __name__, url_prefix="/books")

MAX_BOOK_FILE_BYTES = 20 * 1024 * 1024
TAG_SUGGESTION_CHARS = 5000


def _details(form) -> publishing.BookDetails:
    return publishing.BookDetails(
        title=form.title.data,
        author=form.author.data or "",
        description=form.description.data or "",
        visibility=form.visibility.data,
        status=form.status.data,
        genres=form.genres.data or [],
        moods=form.moods.data or [],
    )


def _chapters_from(storage) -> list:
    """The chapters found in an uploaded book file."""
    return parse_upload(storage.filename, storage.read(MAX_BOOK_FILE_BYTES + 1)).chapters


def _uploaded(file_field):
    """The FileStorage from a form field, or None if nothing was chosen."""
    storage = file_field.data
    return storage if storage and storage.filename else None


@bp.route("/upload", methods=["GET", "POST"])
@login_required
@limiter.limit("20 per hour", methods=["POST"])
def upload():
    form = UploadBookForm()
    if form.validate_on_submit():
        try:
            book_file = _uploaded(form.file)
            parsed = _chapters_from(book_file) if book_file else []
            book = publishing.create_book(
                current_user, _details(form), parsed, _uploaded(form.cover)
            )
        except UploadRejected as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            if book.chapter_count:
                flash("Your book is ready to read.", "success")
                return redirect(url_for("books.detail", book_id=book.id))
            flash("Book created. Add your first chapter to start publishing.", "success")
            return redirect(url_for("books.new_chapter", book_id=book.id))
    return render_template("books/upload.html", form=form)


@bp.get("/<int:book_id>")
def detail(book_id):
    book = readable_book_or_404(book_id)
    context = {"book": book, "is_owner": book.is_owned_by(current_user)}
    if current_user.is_authenticated:
        context["progress"] = reading.get_progress(current_user.id, book.id)
        context["following"] = reading.is_following(current_user.id, book.id)
    return render_template("books/detail.html", **context)


@bp.route("/<int:book_id>/edit", methods=["GET", "POST"])
@login_required
def edit(book_id):
    book = owned_book_or_404(book_id)
    form = EditBookForm(obj=book)
    if form.validate_on_submit():
        try:
            publishing.update_book(
                book, _details(form), _uploaded(form.cover), form.remove_cover.data
            )
        except UploadRejected as error:
            db.session.rollback()
            flash(str(error), "error")
        else:
            flash("Changes saved.", "success")
            return redirect(url_for("books.detail", book_id=book.id))
    return render_template("books/edit.html", form=form, book=book)


@bp.post("/<int:book_id>/delete")
@login_required
def delete(book_id):
    publishing.delete_book(owned_book_or_404(book_id))
    flash("Book deleted.", "info")
    return redirect(url_for("library.shelf"))


@bp.route("/<int:book_id>/chapters/new", methods=["GET", "POST"])
@login_required
def new_chapter(book_id):
    book = owned_book_or_404(book_id)
    form = ChapterForm()
    if form.validate_on_submit():
        chapter = publishing.add_chapter(book, form.title.data, form.body.data)
        flash(f"Published chapter {chapter.number}.", "success")
        return redirect(url_for("books.detail", book_id=book.id))
    return render_template(
        "books/chapter_form.html", form=form, file_form=ChapterFileForm(), book=book
    )


@bp.post("/<int:book_id>/chapters/import")
@login_required
@limiter.limit("20 per hour")
def import_chapters(book_id):
    book = owned_book_or_404(book_id)
    form = ChapterFileForm()
    if not form.validate_on_submit():
        for messages in form.errors.values():
            flash(messages[0], "error")
        return redirect(url_for("books.new_chapter", book_id=book.id))

    try:
        added = publishing.add_chapters(book, _chapters_from(form.file.data))
    except UploadRejected as error:
        db.session.rollback()
        flash(str(error), "error")
        return redirect(url_for("books.new_chapter", book_id=book.id))

    flash(f"Published {len(added)} chapter{'' if len(added) == 1 else 's'}.", "success")
    return redirect(url_for("books.detail", book_id=book.id))


@bp.post("/<int:book_id>/follow")
@login_required
def follow(book_id):
    book = readable_book_or_404(book_id)
    if book.is_owned_by(current_user):
        abort(400)
    wants_follow = request.form.get("action") == "follow"
    reading.set_following(current_user.id, book, wants_follow)
    flash(
        "You'll be notified about new chapters." if wants_follow else "You won't get chapter alerts.",
        "success",
    )
    return redirect(url_for("books.detail", book_id=book.id))


@bp.get("/<int:book_id>/cover")
def cover(book_id):
    book = readable_book_or_404(book_id)
    path = covers.cover_path(book.cover_filename) if book.cover_filename else None
    if path is None or not path.exists():
        abort(404)
    response = send_file(path, mimetype="image/jpeg")
    response.headers["Cache-Control"] = "private, max-age=3600"
    return response


@bp.get("/<int:book_id>/images/<int:image_id>")
@login_required
def image(book_id, image_id):
    book = readable_book_or_404(book_id)
    picture = db.session.get(BookImage, image_id)
    path = chapter_images.store.path(picture.filename) if picture else None
    if picture is None or picture.book_id != book.id or path is None or not path.exists():
        abort(404)
    response = send_file(path, mimetype="image/jpeg")
    response.headers["Cache-Control"] = "private, max-age=86400"
    return response


@bp.post("/suggest-tags")
@login_required
@limiter.limit("30 per minute")
def suggest():
    payload = request.get_json(silent=True)
    text = payload.get("text", "") if isinstance(payload, dict) else ""
    if not isinstance(text, str):
        return jsonify(error="Send text to analyse."), 400
    genres, moods = suggest_tags(text[:TAG_SUGGESTION_CHARS])
    return jsonify(genres=genres, moods=moods)
