from flask import Blueprint, Response, current_app, jsonify, request
from flask_login import login_required

from ..extensions import limiter
from ..services import speech

bp = Blueprint("speech", __name__, url_prefix="/api/speech")


@bp.get("/status")
@login_required
def status():
    """Tells the reader whether the local AI voice is installed, and which voices it offers."""
    return jsonify(
        engine=speech.engine_name(),
        voices=[{"id": key, "label": label} for key, label in speech.voice_choices().items()],
    )


@bp.post("/synthesize")
@login_required
@limiter.limit("120 per minute")
def synthesize():
    payload = request.get_json(silent=True)
    text = payload.get("text") if isinstance(payload, dict) else None
    if not isinstance(text, str) or not text.strip():
        return jsonify(error="Send some text to read."), 400

    limit = current_app.config["SPEECH_MAX_CHARS"]
    if len(text) > limit:
        return jsonify(error=f"Send at most {limit} characters at a time."), 400

    voice = payload.get("voice")
    speed = payload.get("speed")
    try:
        audio = speech.synthesize(
            text,
            voice if isinstance(voice, str) else None,
            float(speed) if isinstance(speed, (int, float)) and not isinstance(speed, bool) else 1.0,
        )
    except speech.SpeechUnavailable as error:
        return jsonify(error=str(error)), 503
    return Response(audio, mimetype="audio/wav")
