"""The Piper voice. Started with a fixed command taken from server configuration; the
text goes in through stdin so nothing a visitor sends ever reaches the command line.
https://github.com/OHF-Voice/piper1-gpl
"""
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from flask import current_app

from .speech_errors import SpeechUnavailable

MAX_PARALLEL = 2
SLOT_WAIT_SECONDS = 5

_slots = threading.BoundedSemaphore(MAX_PARALLEL)
# Stops a console window flashing on Windows each time Piper starts.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _command() -> list[str] | None:
    program = shutil.which(current_app.config["PIPER_BIN"] or "")
    model = current_app.config["PIPER_MODEL"]
    if not program or not model or not Path(model).is_file():
        return None
    return [program, "-m", model]


def is_available() -> bool:
    return _command() is not None


def synthesize(text: str) -> bytes:
    command = _command()
    if command is None:
        raise SpeechUnavailable("The AI voice isn't set up on this computer.")
    if not _slots.acquire(timeout=SLOT_WAIT_SECONDS):
        raise SpeechUnavailable("The voice is busy. Try again in a moment.")

    try:
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "speech.wav"
            subprocess.run(
                [*command, "-f", str(target)],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=current_app.config["PIPER_TIMEOUT_SECONDS"],
                check=True,
                creationflags=_NO_WINDOW,
            )
            return target.read_bytes()
    except (OSError, subprocess.SubprocessError) as error:
        current_app.logger.warning("Piper failed: %s", error)
        raise SpeechUnavailable("The AI voice couldn't read that.") from error
    finally:
        _slots.release()
