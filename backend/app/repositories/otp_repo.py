"""One-time password records for email verification."""
from app.database.mongo import get_db
from app.utils.ids import new_id, now_utc


def _col():
    return get_db()["otp_records"]


def create_otp(data: dict) -> dict:
    doc = {
        "_id": new_id(),
        "user_id": data["user_id"],
        "email": (data.get("email") or "").lower(),
        "purpose": data.get("purpose", "EMAIL_VERIFICATION"),
        "code_hash": data["code_hash"],
        "expires_at": data["expires_at"],
        "attempts": 0,
        "max_attempts": int(data.get("max_attempts", 5)),
        "consumed": False,
        "created_at": now_utc(),
        "last_sent_at": now_utc(),
    }
    _col().insert_one(doc)
    return doc


def invalidate_active(user_id: str, purpose: str = "EMAIL_VERIFICATION") -> int:
    result = _col().update_many(
        {"user_id": user_id, "purpose": purpose, "consumed": False},
        {"$set": {"consumed": True, "invalidated_at": now_utc()}},
    )
    return result.modified_count


def find_active(email: str, purpose: str = "EMAIL_VERIFICATION") -> dict | None:
    cursor = (
        _col()
        .find({"email": (email or "").lower(), "purpose": purpose, "consumed": False})
        .sort("created_at", -1)
        .limit(1)
    )
    return next(cursor, None)


def find_latest(email: str, purpose: str = "EMAIL_VERIFICATION") -> dict | None:
    cursor = (
        _col()
        .find({"email": (email or "").lower(), "purpose": purpose})
        .sort("created_at", -1)
        .limit(1)
    )
    return next(cursor, None)


def increment_attempt(otp_id: str) -> int:
    _col().update_one({"_id": otp_id}, {"$inc": {"attempts": 1}})
    doc = _col().find_one({"_id": otp_id})
    return int((doc or {}).get("attempts", 0))


def consume(otp_id: str) -> bool:
    result = _col().update_one(
        {"_id": otp_id, "consumed": False},
        {"$set": {"consumed": True, "consumed_at": now_utc()}},
    )
    return result.modified_count == 1


def count_since(email: str, since, purpose: str = "EMAIL_VERIFICATION") -> int:
    return _col().count_documents(
        {"email": (email or "").lower(), "purpose": purpose, "created_at": {"$gte": since}}
    )
