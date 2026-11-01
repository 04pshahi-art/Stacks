"""Application configuration.

Everything secret or environment-specific comes from environment variables
(see .env.example). Nothing sensitive is hard-coded here.
"""
import os
import tempfile
from datetime import timedelta
from pathlib import Path

from sqlalchemy.pool import StaticPool

BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "")

    # XAMPP's MariaDB: user "root", empty password, port 3306.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://root:@127.0.0.1:3306/folio?charset=utf8mb4",
    )
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    # Sessions and cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_flag("COOKIE_SECURE", False)  # True behind HTTPS
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    WTF_CSRF_TIME_LIMIT = None  # token lives as long as the session

    # Uploads
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024
    UPLOAD_DIR = INSTANCE_DIR / "covers"
    IMAGE_DIR = INSTANCE_DIR / "images"  # pictures inside books
    MAX_COVER_BYTES = 2 * 1024 * 1024

    # Rate limiting (use redis:// in production, memory:// is per-process)
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True

    # Login protection
    LOGIN_MAX_FAILURES = 5
    LOGIN_LOCKOUT_MINUTES = 15

    # Local AI (Ollama)
    AI_ENABLED = _env_flag("AI_ENABLED", True)
    OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "deepseek-r1:7b")
    # A 7B reasoning model on a normal PC can take a while, so be generous.
    OLLAMA_TIMEOUT_SECONDS = 180
    OLLAMA_MAX_TOKENS = 1024

    # AI voice. Kokoro (sweeter, preferred) or Piper. Leave empty for the browser's voice.
    KOKORO_MODEL = os.environ.get("KOKORO_MODEL", "")  # path to kokoro-v1.0.onnx
    KOKORO_VOICES = os.environ.get("KOKORO_VOICES", "")  # path to voices-v1.0.bin
    PIPER_BIN = os.environ.get("PIPER_BIN", "")  # e.g. "piper" or a full path to piper.exe
    PIPER_MODEL = os.environ.get("PIPER_MODEL", "")  # path to a voice file ending in .onnx
    PIPER_TIMEOUT_SECONDS = 40
    SPEECH_MAX_CHARS = 600

    # Recommendations unlock after this many books have been read
    MIN_BOOKS_FOR_RECOMMENDATIONS = 3

    BOOKS_PER_PAGE = 24


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-key-not-for-production"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    # One shared in-memory connection so every request sees the same data.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }
    RATELIMIT_ENABLED = False
    AI_ENABLED = False
    UPLOAD_DIR = Path(tempfile.gettempdir()) / "folio-test-covers"
    IMAGE_DIR = Path(tempfile.gettempdir()) / "folio-test-images"
