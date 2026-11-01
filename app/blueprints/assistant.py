from flask import Blueprint, jsonify, request, url_for
from flask_login import current_user, login_required

from ..extensions import limiter
from ..services import assistant, ollama_client

bp = Blueprint("assistant", __name__, url_prefix="/api/assistant")


def _book_payload(book) -> dict:
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "mood": book.mood_slug,
        "url": url_for("books.detail", book_id=book.id),
    }


@bp.get("/status")
@login_required
def status():
    return jsonify(online=ollama_client.is_available())


@bp.post("/chat")
@login_required
@limiter.limit("15 per minute")
def chat():
    payload = request.get_json(silent=True)
    message = payload.get("message") if isinstance(payload, dict) else None
    if not isinstance(message, str) or not message.strip():
        return jsonify(error="Type a message first."), 400
    if len(message) > assistant.MAX_MESSAGE_CHARS:
        return jsonify(error=f"Keep messages under {assistant.MAX_MESSAGE_CHARS} characters."), 400

    reply = assistant.reply_to(current_user, message, payload.get("history"))
    return jsonify(
        reply=reply.text,
        books=[_book_payload(book) for book in reply.books],
        online=reply.ai_online,
    )
