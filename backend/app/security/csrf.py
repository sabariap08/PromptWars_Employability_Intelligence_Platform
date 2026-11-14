"""Double-submit CSRF protection for state-changing API requests."""
import hmac
import secrets

from flask import current_app, request, session

from app.utils.responses import AppError

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def get_csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def init_csrf(app) -> None:
    @app.before_request
    def verify_csrf():
        if not app.config.get("CSRF_ENABLED", True):
            return None
        if request.method in SAFE_METHODS:
            return None
        if not request.path.startswith("/api/"):
            return None
        expected = session.get("csrf_token")
        provided = request.headers.get("X-CSRF-Token", "")
        if not expected or not provided or not hmac.compare_digest(expected, provided):
            raise AppError(
                "Your session could not be verified. Refresh the page and try again.",
                "CSRF_FAILED",
                403,
            )
        return None
