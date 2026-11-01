"""Security helpers: response headers, password policy, safe redirects, LIKE escaping."""
import re
from urllib.parse import urljoin, urlparse

from flask import request

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' https://fonts.googleapis.com",
        "font-src https://fonts.gstatic.com",
        "img-src 'self' data:",
        "connect-src 'self'",
        "media-src 'self' blob:",  # the AI voice plays generated audio
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)

_STATIC_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


def apply_security_headers(response, *, secure_cookies: bool):
    """after_request hook. Dynamic pages are never cached by the browser."""
    for name, value in _STATIC_HEADERS.items():
        response.headers.setdefault(name, value)
    if secure_cookies:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    if request.endpoint != "static":
        response.headers.setdefault("Cache-Control", "no-store")
    return response


# --- redirects -----------------------------------------------------------
def is_safe_redirect_target(target: str | None) -> bool:
    """Only allow same-site relative URLs (blocks open-redirect attacks)."""
    if not target or not target.startswith("/") or target.startswith("//"):
        return False
    base = urlparse(request.host_url)
    resolved = urlparse(urljoin(request.host_url, target))
    return resolved.scheme in {"http", "https"} and resolved.netloc == base.netloc


# --- search --------------------------------------------------------------
def escape_like(term: str) -> str:
    """Escape LIKE wildcards so user text is matched literally."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# --- passwords -----------------------------------------------------------
PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 128

_COMMON_PASSWORDS = frozenset(
    {
        "password", "password1", "password123", "1234567890", "12345678910",
        "qwertyuiop", "qwerty123", "letmein123", "iloveyou123", "welcome123",
        "admin12345", "abc1234567", "passw0rd123", "changeme123", "football123",
        "0123456789", "1q2w3e4r5t", "monkey1234", "dragon1234", "baseball123",
    }
)


def password_problems(password: str, *, username: str = "", email: str = "") -> list[str]:
    """Return every reason the password is unacceptable (empty list = fine)."""
    problems = []
    lowered = password.lower()

    if len(password) < PASSWORD_MIN_LENGTH:
        problems.append(f"Use at least {PASSWORD_MIN_LENGTH} characters.")
    if len(password) > PASSWORD_MAX_LENGTH:
        problems.append(f"Use at most {PASSWORD_MAX_LENGTH} characters.")
    if lowered in _COMMON_PASSWORDS or len(set(lowered)) <= 3:
        problems.append("That password is too easy to guess.")

    classes = [
        re.search(r"[a-z]", password),
        re.search(r"[A-Z]", password),
        re.search(r"\d", password),
        re.search(r"[^A-Za-z0-9]", password),
    ]
    if sum(1 for found in classes if found) < 2:
        problems.append("Mix at least two of: lowercase, uppercase, numbers, symbols.")

    identity_parts = [username.lower(), email.split("@")[0].lower()]
    if any(len(part) >= 3 and part in lowered for part in identity_parts):
        problems.append("Don't include your username or email in your password.")

    return problems
