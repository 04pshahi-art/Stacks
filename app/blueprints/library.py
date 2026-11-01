from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from ..services import queries, recommender
from ..services.catalog import GENRES, MOODS

bp = Blueprint("library", __name__)


def _search_filters() -> dict:
    """Read and sanitise the search form from the query string."""
    genre = request.args.get("genre", "")
    mood = request.args.get("mood", "")
    sort = request.args.get("sort", "newest")
    return {
        "q": request.args.get("q", "").strip()[: queries.MAX_QUERY_LENGTH],
        "genre": genre if genre in GENRES else "",
        "mood": mood if mood in MOODS else "",
        "sort": sort if sort in queries.SORT_OPTIONS else "newest",
    }


@bp.get("/")
def home():
    filters = _search_filters()
    page = max(1, request.args.get("page", 1, type=int) or 1)
    context = {
        "filters": filters,
        "genres": GENRES,
        "moods": MOODS,
        "sort_options": queries.SORT_OPTIONS,
    }

    if filters["q"] or filters["genre"] or filters["mood"]:
        results = queries.search_books(
            text=filters["q"],
            genre=filters["genre"],
            mood=filters["mood"],
            sort=filters["sort"],
            page=page,
            per_page=24,
        )
        return render_template("library/home.html", results=results, **context)

    shelves = {"latest": queries.latest_public(12), "popular": queries.popular_public(8)}
    if current_user.is_authenticated:
        taste = recommender.build_taste(current_user)
        shelves.update(
            reading=queries.continue_reading(current_user.id, limit=6),
            taste=taste,
            picks=recommender.recommend(current_user, taste, limit=8),
        )
    return render_template("library/home.html", results=None, **shelves, **context)


@bp.get("/library")
@login_required
def shelf():
    return render_template(
        "library/shelf.html",
        reading=queries.continue_reading(current_user.id, limit=None),
        finished=queries.finished_books(current_user.id),
        uploads=queries.uploaded_books(current_user.id),
    )
