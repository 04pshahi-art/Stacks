"""The AI voice, tested against a stand-in for the Kokoro library."""
import importlib.machinery
import sys
import types

import numpy as np
import pytest
from flask import Flask


@pytest.fixture
def kokoro(tmp_path, monkeypatch):
    calls = []

    class FakeKokoro:
        def __init__(self, model, voices):
            calls.append(("load",))

        def create(self, text, voice, speed, lang):
            calls.append((text, voice, speed, lang))
            if "BOOM" in text:
                raise RuntimeError("model failed")
            return np.sin(np.linspace(0, 100, 2400)).astype("float32"), 24000

    fake = types.ModuleType("kokoro_onnx")
    fake.Kokoro = FakeKokoro
    fake.__spec__ = importlib.machinery.ModuleSpec("kokoro_onnx", None)
    monkeypatch.setitem(sys.modules, "kokoro_onnx", fake)

    from app.services import kokoro_voice

    monkeypatch.setattr(kokoro_voice, "_engine", None)
    (tmp_path / "k.onnx").write_bytes(b"x")
    (tmp_path / "k.bin").write_bytes(b"x")
    app = Flask("t")
    app.config.update(
        KOKORO_MODEL=str(tmp_path / "k.onnx"), KOKORO_VOICES=str(tmp_path / "k.bin"),
        PIPER_BIN="", PIPER_MODEL="", SPEECH_MAX_CHARS=600,
    )
    with app.app_context():
        yield calls


def test_text_becomes_wav_audio(kokoro):
    from app.services import speech

    audio = speech.synthesize("Hello there.", "bf_emma", 1.05)
    assert audio[:4] == b"RIFF" and audio[8:12] == b"WAVE"
    assert kokoro[-1] == ("Hello there.", "bf_emma", 1.05, "en-gb")


def test_unknown_voice_and_silly_speed_are_corrected(kokoro):
    from app.services import speech

    speech.synthesize("Hi", "../../etc/passwd", 99)
    assert kokoro[-1] == ("Hi", "af_heart", 1.3, "en-us")


def test_long_text_is_truncated_and_empty_text_refused(kokoro):
    from app.services import speech

    speech.synthesize("a" * 5000)
    assert len(kokoro[-1][0]) == 600
    with pytest.raises(speech.SpeechUnavailable):
        speech.synthesize("   ")


def test_model_errors_become_a_safe_message(kokoro):
    from app.services import speech

    with pytest.raises(speech.SpeechUnavailable, match="couldn't read"):
        speech.synthesize("BOOM")


def test_nothing_is_available_without_the_model_files():
    from app.services import speech

    app = Flask("t")
    app.config.update(KOKORO_MODEL="", KOKORO_VOICES="", PIPER_BIN="", PIPER_MODEL="", SPEECH_MAX_CHARS=600)
    with app.app_context():
        assert speech.engine_name() is None
