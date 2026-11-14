"""Central configuration loaded from environment variables only."""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, "true" if default else "false").strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


class Config:
    APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()
    IS_PRODUCTION = APP_ENV == "production"
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    DEBUG = _bool("FLASK_DEBUG", False) and not IS_PRODUCTION

    MONGODB_URI = os.environ.get("MONGODB_URI", "").strip()
    MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME", "eip")
    SEED_DEMO_ON_START = _bool("SEED_DEMO_ON_START", True)

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    MAX_CONTENT_LENGTH = _int("MAX_UPLOAD_MB", 5) * 1024 * 1024

    CSRF_ENABLED = _bool("CSRF_ENABLED", True)
    RATELIMIT_ENABLED = _bool("RATELIMIT_ENABLED", True)

    EMAIL_DELIVERY = os.environ.get("EMAIL_DELIVERY", "console")
    EXPOSE_VERIFICATION_LINK = _bool("EXPOSE_VERIFICATION_LINK", not IS_PRODUCTION)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT = _int("MAIL_PORT", 587)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_FROM = os.environ.get("MAIL_FROM", "no-reply@eip.local")

    AI_PRIMARY_PROVIDER = os.environ.get("AI_PRIMARY_PROVIDER", "").strip().lower()
    AI_FALLBACK_ORDER = os.environ.get(
        "AI_FALLBACK_ORDER", "groq,gemini,openrouter,huggingface,ollama"
    )
    AI_TIMEOUT_SECONDS = _int("AI_TIMEOUT_SECONDS", 25)

    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
    GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
    OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct")
    HF_API_KEY = os.environ.get("HF_API_KEY", "").strip()
    HF_MODEL = os.environ.get("HF_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
    OLLAMA_ENABLED = _bool("OLLAMA_ENABLED", False)
    OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "").strip()
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1")

    MAX_ASSESSMENT_ATTEMPTS = _int("MAX_ASSESSMENT_ATTEMPTS", 5)

    SUPER_ADMIN_EMAIL = os.environ.get("SUPER_ADMIN_EMAIL", "").strip().lower()
    SUPER_ADMIN_PASSWORD = os.environ.get("SUPER_ADMIN_PASSWORD", "")
    SUPER_ADMIN_NAME = os.environ.get("SUPER_ADMIN_NAME", "Platform Owner")

    UPLOAD_DIR = str(PROJECT_ROOT / "instance" / "uploads")
