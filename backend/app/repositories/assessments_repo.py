"""Assessment definitions, attempts and integrity events."""
from app.database.mongo import get_db
from app.utils.ids import new_id, now_utc


def _assessments():
    return get_db()["assessments"]


def _attempts():
    return get_db()["assessment_attempts"]


def _integrity():
    return get_db()["assessment_integrity_events"]


def create_assessment(data: dict) -> dict:
    doc = {
        "_id": new_id(),
        "user_id": data["user_id"],
        "organization_id": data.get("organization_id"),
        "purpose": data.get("purpose", "BASELINE"),
        "title": data.get("title", "Assessment"),
        "skill_names": data.get("skill_names", []),
        "question_ids": data.get("question_ids", []),
        "time_limit_seconds": int(data.get("time_limit_seconds", 1200)),
        "related_id": data.get("related_id"),
        "status": "READY",
        "created_at": now_utc(),
    }
    _assessments().insert_one(doc)
    return doc


def find_assessment(assessment_id: str, user_id: str | None = None) -> dict | None:
    query = {"_id": assessment_id}
    if user_id:
        query["user_id"] = user_id
    return _assessments().find_one(query)


def list_assessments(user_id: str) -> list:
    return list(_assessments().find({"user_id": user_id}).sort("created_at", -1).limit(30))


def create_attempt(data: dict) -> dict:
    doc = {
        "_id": new_id(),
        "user_id": data["user_id"],
        "organization_id": data.get("organization_id"),
        "assessment_id": data["assessment_id"],
        "purpose": data.get("purpose", "BASELINE"),
        "title": data.get("title", "Assessment"),
        "status": "IN_PROGRESS",
        "attempt_number": int(data.get("attempt_number", 1)),
        "questions": data.get("questions", []),
        "answer_key": data.get("answer_key", {}),
        "started_at": now_utc(),
        "expires_at": data.get("expires_at"),
        "submitted_at": None,
        "evaluated_at": None,
        "answers": [],
        "score": None,
        "topic_scores": {},
        "integrity": {},
        "summary": "",
        "created_at": now_utc(),
    }
    _attempts().insert_one(doc)
    return doc


def find_attempt(attempt_id: str, user_id: str | None = None) -> dict | None:
    query = {"_id": attempt_id}
    if user_id:
        query["user_id"] = user_id
    return _attempts().find_one(query)


def save_attempt(attempt: dict) -> None:
    _attempts().replace_one({"_id": attempt["_id"]}, attempt)


def list_attempts(user_id: str, purpose: str | None = None) -> list:
    query = {"user_id": user_id}
    if purpose:
        query["purpose"] = purpose
    return list(_attempts().find(query).sort("created_at", -1))


def list_org_attempts(org_id: str) -> list:
    return list(_attempts().find({"organization_id": org_id, "status": "EVALUATED"}))


def latest_evaluated_attempt(user_id: str) -> dict | None:
    attempts = list(
        _attempts()
        .find({"user_id": user_id, "status": "EVALUATED"})
        .sort("evaluated_at", -1)
        .limit(1)
    )
    return attempts[0] if attempts else None


def count_active_attempts(assessment_id: str, user_id: str) -> int:
    return _attempts().count_documents(
        {"assessment_id": assessment_id, "user_id": user_id, "status": "IN_PROGRESS"}
    )


def count_attempts_for_assessment(assessment_id: str, user_id: str) -> int:
    return _attempts().count_documents({"assessment_id": assessment_id, "user_id": user_id})


def add_integrity_events(events: list) -> None:
    if events:
        _integrity().insert_many(events)


def list_integrity_events(attempt_id: str) -> list:
    return list(_integrity().find({"attempt_id": attempt_id}).sort("at", 1))


def count_attempts(user_id: str | None = None) -> int:
    query = {"user_id": user_id} if user_id else {}
    return _attempts().count_documents(query)
