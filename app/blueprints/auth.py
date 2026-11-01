from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import limiter, login_manager
from ..forms import LoginForm, RegisterForm
from ..security import is_safe_redirect_target
from ..services import accounts

bp = Blueprint("auth", __name__)

LOGIN_FAILED_MESSAGE = "Those details didn't work, or the account is temporarily locked. Try again in a few minutes."


@login_manager.user_loader
def _load_user(session_id):
    return accounts.load_user(session_id)


@login_manager.unauthorized_handler
def _unauthorized():
    if request.path.startswith("/api/"):
        return jsonify(error="Sign in to continue."), 401
    flash("Sign in to continue.", "info")
    return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))


def _start_session(user) -> None:
    """Log in with a fresh session (prevents session fixation)."""
    session.clear()
    login_user(user)
    session.permanent = True


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("library.home"))

    form = RegisterForm()
    if form.validate_on_submit():
        try:
            user = accounts.register_user(form.username.data, form.email.data, form.password.data)
        except accounts.AccountExists:
            form.username.errors.append("That username or email is already registered.")
        else:
            _start_session(user)
            return redirect(url_for("account.preferences", welcome=1))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("library.home"))

    form = LoginForm()
    if form.validate_on_submit():
        user = accounts.authenticate(form.identifier.data, form.password.data)
        if user:
            _start_session(user)
            target = request.args.get("next")
            return redirect(target if is_safe_redirect_target(target) else url_for("library.home"))
        flash(LOGIN_FAILED_MESSAGE, "error")
    return render_template("auth/login.html", form=form)


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    flash("You're signed out.", "info")
    return redirect(url_for("library.home"))
