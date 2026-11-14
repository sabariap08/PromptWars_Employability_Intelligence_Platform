"""Small text helpers shared across services."""
import re
import unicodedata
from pathlib import PurePath


def clean_text(value, max_length: int = 5000) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text[:max_length]


def normalize_email(value: str) -> str:
    return clean_text(value, 320).lower()


def is_valid_email(value: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$", value or ""))


def is_http_url(value: str) -> bool:
    return bool(re.match(r"^https?://[^\s]+$", value or "", re.IGNORECASE))


def safe_filename(original: str) -> str:
    name = PurePath(original or "file").name
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", normalized).strip("._-")
    return cleaned[:120] or "upload"


def truncate(value, limit: int = 180) -> str:
    text = clean_text(value, 4000)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
