class SpeechUnavailable(Exception):
    """The local voice isn't installed, is busy, or failed. The message is safe to show."""
