"""Flask application factory for the Employability Intelligence Platform."""
import logging
import os
from datetime import date, datetime

from flask import Flask, jsonify, render_template, request
from flask.json.provider import DefaultJSONProvider

from app.config.settings import PROJECT_ROOT, Config


class ISOJSONProvider(DefaultJSONProvider):
    """Serialize datetimes as ISO strings and sets as lists."""

    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, set):
            return sorted(obj)
        return super().default(obj)


def _register_error_handlers(app: Flask) -> None:
    from app.utils.responses import AppError, fail

    def wants_json() -> bool:
        return request.path.startswith("/api/") or request.is_json

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        if wants_json():
            return fail(error.message, error.code, error.status, error.details)
        return (
            render_template("errors/error.html", status=error.status, message=error.message),
            error.status,
        )

    @app.errorhandler(404)
    def not_found(error):
        if wants_json():
            return fail("The requested resource was not found.", "NOT_FOUND", 404)
        return render_template("errors/404.html"), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        if wants_json():
            return fail("This action is not allowed.", "METHOD_NOT_ALLOWED", 405)
        return render_template("errors/error.html", status=405, message="This action is not allowed."), 405

    @app.errorhandler(413)
    def payload_too_large(error):
        limit_mb = app.config.get("MAX_CONTENT_LENGTH", 0) // (1024 * 1024)
        message = f"Your file is too large. Maximum size is {limit_mb} MB."
        if wants_json():
            return fail(message, "FILE_TOO_LARGE", 413)
        return render_template("errors/error.html", status=413, message=message), 413

    @app.errorhandler(429)
    def rate_limited(error):
        if wants_json():
            return fail("Too many attempts. Please wait a moment and try again.", "RATE_LIMITED", 429)
        return (
            render_template("errors/error.html", status=429, message="Too many attempts. Please wait a moment."),
            429,
        )

    @app.errorhandler(500)
    def server_error(error):
        app.logger.exception("Unhandled server error")
        if wants_json():
            return fail("Something went wrong on our side. Please try again.", "SERVER_ERROR", 500)
        return render_template("errors/500.html"), 500


def _register_security_headers(app: Flask) -> None:
    @app.after_request
    def add_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        if app.config.get("IS_PRODUCTION"):
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'self'; img-src 'self' data: https:; "
                "style-src 'self' 'unsafe-inline'; "
                "script-src 'self'; font-src 'self'; connect-src 'self'; frame-ancestors 'none'",
            )
        return response


def create_app(overrides: dict | None = None) -> Flask:
    base_dir = PROJECT_ROOT
    app = Flask(
        __name__,
        template_folder=str(base_dir / "frontend" / "templates"),
        static_folder=str(base_dir / "frontend" / "static"),
        static_url_path="/static",
    )
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    app.json = ISOJSONProvider(app)
    app.config.setdefault("APP_NAME", "Employability Intelligence Platform")
    app.extensions["app_name"] = app.config["APP_NAME"]

    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    from app.database.mongo import init_database

    init_database(app)

    from app.security.csrf import init_csrf
    from app.security.rate_limit import limiter

    init_csrf(app)
    limiter.init_app(app)

    from app.ai_providers.provider_manager import build_provider_manager
    from app.repositories import operations_repo

    with app.app_context():
        settings = operations_repo.get_provider_settings() or {}
        app.extensions["ai_manager"] = build_provider_manager(
            app,
            {
                "primary_provider": settings.get("primary_provider"),
                "fallback_order": settings.get("fallback_order"),
            },
        )

    from app.api import register_api_blueprints
    from app.pages import bp as pages_bp

    register_api_blueprints(app)
    app.register_blueprint(pages_bp)

    @app.context_processor
    def inject_globals():
        from app.security.auth import current_user
        from app.security.csrf import get_csrf_token

        return {
            "current_user": current_user(),
            "csrf_token": get_csrf_token(),
            "app_name": app.config["APP_NAME"],
            "db_mode": app.extensions.get("db_mode", "memory"),
        }

    _register_error_handlers(app)
    _register_security_headers(app)

    from app.database.seed import ensure_seed

    with app.app_context():
        try:
            ensure_seed(app)
        except Exception:  # seeding must never prevent the app from starting
            app.logger.exception("Seeding failed; continuing with an empty catalog")

    return app
