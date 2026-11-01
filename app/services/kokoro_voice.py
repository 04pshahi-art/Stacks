"""The Kokoro voice: a small, sweet-sounding neural voice that runs on the CPU.

Uses the kokoro-onnx package with two files you download once (see the README).
The model is loaded the first time it is needed and kept in memory.
https://github.com/thewh1teagle/kokoro-onnx
"""
import importlib.util
import io
import threading
import wave
from pathlib import Path

import numpy as np
from flask import current_app

from .speech_errors import SpeechUnavailable

# Voices offered in the reader, by the name Kokoro uses. The first is the default.
VOICES = {
    "af_heart": "Heart: warm, sweet (US woman)",
    "af_bella": "Bella: bright, expressive (US woman)",
    "af_nicole": "Nicole: soft, calm (US woman)",
    "af_sky": "Sky: light, gentle (US woman)",
    "bf_emma": "Emma: smooth storyteller (UK woman)",
    "bf_isabella": "Isabella: melodious (UK woman)",
    "am_michael": "Michael: warm (US man)",
    "bm_george": "George: deep storyteller (UK man)",
}
DEFAULT_VOICE = next(iter(VOICES))
MIN_SPEED, MAX_SPEED = 0.7, 1.3
WAIT_SECONDS = 20

_load_lock = threading.Lock()
_run_lock = threading.Lock()  # one sentence at a time: the model uses all CPU cores anyway
_engine = None


def _files() -> tuple[Path, Path] | None:
    model = Path(current_app.config["KOKORO_MODEL"] or "")
    voices = Path(current_app.config["KOKORO_VOICES"] or "")
    return (model, voices) if model.is_file() and voices.is_file() else None


def is_available() -> bool:
    return _files() is not None and importlib.util.find_spec("kokoro_onnx") is not None


def _load():
    global _engine
    with _load_lock:
        if _engine is None:
            from kokoro_onnx import Kokoro

            model, voices = _files()
            _engine = Kokoro(str(model), str(voices))
        return _engine


def _to_wav(samples, rate: int) -> bytes:
    pcm = (np.clip(np.asarray(samples), -1, 1) * 32767).astype("<i2")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(pcm.tobytes())
    return buffer.getvalue()


def synthesize(text: str, voice: str | None = None, speed: float = 1.0) -> bytes:
    if not is_available():
        raise SpeechUnavailable("The AI voice isn't set up on this computer.")
    voice = voice if voice in VOICES else DEFAULT_VOICE
    speed = min(MAX_SPEED, max(MIN_SPEED, speed))
    language = "en-gb" if voice.startswith("b") else "en-us"

    if not _run_lock.acquire(timeout=WAIT_SECONDS):
        raise SpeechUnavailable("The voice is busy. Try again in a moment.")
    try:
        samples, rate = _load().create(text, voice=voice, speed=speed, lang=language)
        return _to_wav(samples, rate)
    except Exception as error:  # the model library can raise almost anything
        current_app.logger.warning("Kokoro failed: %s", error)
        raise SpeechUnavailable("The AI voice couldn't read that.") from error
    finally:
        _run_lock.release()
