"""Text to speech with a voice that runs on this computer.

Kokoro is used when it is set up, otherwise Piper. Both need server-side configuration;
a visitor only ever supplies the text, a voice name from a fixed list, and a speed.
"""
from flask import current_app

from . import kokoro_voice, piper_voice
from .speech_errors import SpeechUnavailable
from .text import clean_text

MAX_WAV_BYTES = 20 * 1024 * 1024

__all__ = ["SpeechUnavailable", "engine_name", "is_available", "voice_choices", "synthesize"]


def engine_name() -> str | None:
    if kokoro_voice.is_available():
        return "kokoro"
    return "piper" if piper_voice.is_available() else None


def is_available() -> bool:
    return engine_name() is not None


def voice_choices() -> dict[str, str]:
    """Voices the reader may pick from (only Kokoro has more than one)."""
    return kokoro_voice.VOICES if engine_name() == "kokoro" else {}


def synthesize(text: str, voice: str | None = None, speed: float = 1.0) -> bytes:
    """Speak `text` and return it as WAV audio."""
    engine = engine_name()
    if engine is None:
        raise SpeechUnavailable("The AI voice isn't set up on this computer.")
    spoken = clean_text(text)[: current_app.config["SPEECH_MAX_CHARS"]]
    if not spoken:
        raise SpeechUnavailable("There is nothing to read.")

    audio = (
        kokoro_voice.synthesize(spoken, voice, speed)
        if engine == "kokoro"
        else piper_voice.synthesize(spoken)
    )
    if not audio or len(audio) > MAX_WAV_BYTES:
        raise SpeechUnavailable("The AI voice returned nothing usable.")
    return audio
