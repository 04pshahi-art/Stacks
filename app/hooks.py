"""Cross-cutting request hooks: security headers, template context, error pages."""
from flask import jsonify, render_template, request
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import HTTPException

from .blueprints.notifications import unread_count
from .security import apply_security_headers

ERROR_COPY = {
    400: ("That didn't work", "Reload the page and try again."),
    403: ("You can't do that", "This belongs to someone else."),
    404: ("We couldn't find that", "The page may have moved, or the book may be private."),
    413: ("That file is too big", "Upload a file under 20 MB."),
    429: ("Slow down a little", "Too many requests. Wait a minute and try again."),
    500: ("Something broke on our side", "Try again in a moment."),
}


def _error_response(status: int, message: str | None = None):
    title, hint = ERROR_COPY.get(status, ERROR_COPY[500])
    if request.path.startswith("/api/"):
        return jsonify(error=message or hint), status
    return render_template("errors/error.html", status=status, title=title, hint=message or hint), status


def register_hooks(app) -> None:
    @app.after_request
    def _headers(response):
        return apply_security_headers(response, secure_cookies=app.config["SESSION_COOKIE_SECURE"])

    @app.context_processor
    def _template_globals():
        unread = unread_count(current_user.id) if current_user.is_authenticated else 0
        return {"unread_count": unread}

    @app.errorhandler(CSRFError)
    def _csrf_failed(_error):
        return _error_response(400, "Your session expired. Reload the page and try again.")

    @app.errorhandler(HTTPException)
    def _http_error(error):
        if error.code in ERROR_COPY:
            return _error_response(error.code)
        return error

    @app.errorhandler(Exception)
    def _unexpected(error):
        app.logger.exception("Unhandled error: %s", error)
        return _error_response(500)
