"""Reusable request validation helpers. All raise AppError on failure."""
import re

from app.utils.responses import AppError
from app.utils.text import clean_text, is_valid_email, normalize_email

PASSWORD_MIN_LENGTH = 8
PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).+$")


def require_fields(payload: dict, fields) -> None:
    if not isinstance(payload, dict):
        raise AppError("Request body must be a JSON object.", "INVALID_BODY", 422)
    missing = [field for field in fields if not clean_text(payload.get(field))]
    if missing:
        raise AppError(
            "Please complete all required fields.",
            "VALIDATION_ERROR",
            422,
            {"missing_fields": missing},
        )


def require_string(payload: dict, field: str, label: str, max_length: int = 4000) -> str:
    value = clean_text(payload.get(field), max_length)
    if not value:
        raise AppError(f"{label} is required.", "VALIDATION_ERROR", 422, {"field": field})
    return value


def validate_email(value: str) -> str:
    email = normalize_email(value)
    if not is_valid_email(email):
        raise AppError("Please enter a valid email address.", "INVALID_EMAIL", 422, {"field": "email"})
    return email


def validate_password(password: str, confirm: str) -> None:
    if len(password or "") < PASSWORD_MIN_LENGTH:
        raise AppError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters long.",
            "WEAK_PASSWORD",
            422,
            {"field": "password"},
        )
    if not PASSWORD_PATTERN.match(password or ""):
        raise AppError(
            "Password must contain at least one letter and one number.",
            "WEAK_PASSWORD",
            422,
            {"field": "password"},
        )
    if password != confirm:
        raise AppError("Passwords do not match.", "PASSWORD_MISMATCH", 422, {"field": "confirm_password"})


def validate_choice(value: str, allowed, label: str) -> str:
    choice = clean_text(value, 80).upper()
    if choice not in allowed:
        raise AppError(f"Invalid {label}.", "INVALID_CHOICE", 422, {"allowed": list(allowed)})
    return choice


def validate_email_domain(email: str, website: str) -> None:
    """Soft validation used for organization registration (never auto-rejects)."""
    return None
