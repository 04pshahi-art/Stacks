from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user

from ..extensions import db, limiter
from ..forms import ChangePasswordForm, PreferencesForm
from ..models import GENRE, MOOD
from ..services import accounts, queries, recommender

bp = Blueprint("account", __name__, url_prefix="/me")


@bp.get("")
@login_required
def profile():
    taste = recommender.build_taste(current_user)
    return render_template(
        "account/profile.html",
        taste=taste,
        top_genres=taste.top(GENRE),
        top_moods=taste.top(MOOD),
        finished_count=len(queries.finished_books(current_user.id)),
        upload_count=len(queries.uploaded_books(current_user.id)),
    )


@bp.route("/preferences", methods=["GET", "POST"])
@login_required
def preferences():
    welcome = request.args.get("welcome") == "1"
    form = PreferencesForm(
        data={
            "genres": current_user.preference_values(GENRE),
            "moods": current_user.preference_values(MOOD),
        }
    )
    if form.validate_on_submit():
        current_user.set_preferences(GENRE, form.genres.data)
        current_user.set_preferences(MOOD, form.moods.data)
        current_user.onboarded = True
        db.session.commit()
        flash("Your taste is saved. Recommendations will follow it.", "success")
        return redirect(url_for("library.home"))
    return render_template("account/preferences.html", form=form, welcome=welcome)


@bp.route("/password", methods=["GET", "POST"])
@login_required
@limiter.limit("5 per hour", methods=["POST"])
def password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if accounts.change_password(current_user, form.current_password.data, form.password.data):
            # The old session id is now invalid; sign this browser back in.
            session.clear()
            login_user(current_user)
            session.permanent = True
            flash("Password changed. Other devices have been signed out.", "success")
            return redirect(url_for("account.profile"))
        form.current_password.errors.append("That isn't your current password.")
    return render_template("account/password.html", form=form)
