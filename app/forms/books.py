from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import BooleanField, RadioField, SelectMultipleField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, ValidationError

from ..models import Book
from ..services.catalog import GENRE_CHOICES, MAX_TAGS_PER_KIND, MOOD_CHOICES
from ..services.importing import ALLOWED_EXTENSIONS

MAX_CHAPTER_CHARS = 300_000


def _at_most_three(form, field):
    if len(field.data or []) > MAX_TAGS_PER_KIND:
        raise ValidationError(f"Pick up to {MAX_TAGS_PER_KIND}.")


class _TagFields:
    genres = SelectMultipleField("Genres", choices=GENRE_CHOICES, validators=[_at_most_three])
    moods = SelectMultipleField("Moods", choices=MOOD_CHOICES, validators=[_at_most_three])


class PreferencesForm(_TagFields, FlaskForm):
    """Favourite genres and moods. No validators beyond the shared limits."""


class BookForm(_TagFields, FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    author = StringField("Author", validators=[Optional(), Length(max=120)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=2000)])
    visibility = RadioField(
        "Who can read it",
        choices=[(Book.PRIVATE, "Only me"), (Book.PUBLIC, "Everyone")],
        default=Book.PRIVATE,
    )
    status = RadioField(
        "Publishing status",
        choices=[(Book.COMPLETE, "Complete"), (Book.ONGOING, "Ongoing, I'll add chapters")],
        default=Book.COMPLETE,
    )
    cover = FileField(
        "Cover image",
        validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Use a JPEG, PNG or WebP image.")],
    )


class UploadBookForm(BookForm):
    file = FileField(
        "Book file",
        validators=[
            FileAllowed(list(ALLOWED_EXTENSIONS), "Upload a .txt, .md, .epub, .pdf or .zip file.")
        ],
    )


class EditBookForm(BookForm):
    remove_cover = BooleanField("Remove the current cover")


class ChapterForm(FlaskForm):
    title = StringField("Chapter title", validators=[DataRequired(), Length(max=200)])
    body = TextAreaField(
        "Text", validators=[DataRequired(), Length(max=MAX_CHAPTER_CHARS)]
    )


class ChapterFileForm(FlaskForm):
    """Add many chapters at once from a file."""

    file = FileField(
        "Chapters file",
        validators=[
            FileRequired("Choose a file first."),
            FileAllowed(list(ALLOWED_EXTENSIONS), "Upload a .txt, .md, .epub, .pdf or .zip file."),
        ],
    )
