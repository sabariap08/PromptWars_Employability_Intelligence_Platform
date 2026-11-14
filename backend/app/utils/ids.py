"""Identifier and timestamp helpers."""
import uuid
from datetime import datetime, timezone


def new_id() -> str:
    return uuid.uuid4().hex


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
