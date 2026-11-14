"""Learning roadmaps, activity, progress records and mentor conversations."""
from app.database.mongo import get_db
from app.utils.ids import new_id, now_utc


def _roadmaps():
    return get_db()["learning_roadmaps"]


def _activity():
    return get_db()["learning_activity"]


def _progress():
    return get_db()["progress_records"]


def _mentor():
    return get_db()["mentor_conversations"]


def create_roadmap(data: dict) -> dict:
    doc = {
        "_id": new_id(),
        "user_id": data["user_id"],
        "organization_id": data.get("organization_id"),
        "career_role_id": data.get("career_role_id"),
        "career_name": data.get("career_name", ""),
        "version": int(data.get("version", 1)),
        "status": "ACTIVE",
        "trigger": data.get("trigger", "initial"),
        "rationale": data.get("rationale", ""),
        "readiness_snapshot": data.get("readiness_snapshot", 0),
        "phases": data.get("phases", []),
        "estimated_hours": data.get("estimated_hours", 0),
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    _roadmaps().insert_one(doc)
    return doc


def find_roadmap(roadmap_id: str) -> dict | None:
    return _roadmaps().find_one({"_id": roadmap_id})


def active_roadmap(user_id: str) -> dict | None:
    return _roadmaps().find_one({"user_id": user_id, "status": "ACTIVE"})


def list_roadmaps(user_id: str) -> list:
    return list(_roadmaps().find({"user_id": user_id}).sort("created_at", -1))


def save_roadmap(roadmap: dict) -> None:
    roadmap["updated_at"] = now_utc()
    _roadmaps().replace_one({"_id": roadmap["_id"]}, roadmap)


def archive_active_roadmaps(user_id: str) -> None:
    _roadmaps().update_many(
        {"user_id": user_id, "status": "ACTIVE"},
        {"$set": {"status": "ARCHIVED", "updated_at": now_utc()}},
    )


def next_version(user_id: str) -> int:
    latest = list(_roadmaps().find({"user_id": user_id}).sort("version", -1).limit(1))
    return (latest[0]["version"] + 1) if latest else 1


def record_activity(data: dict) -> dict:
    doc = {
        "_id": new_id(),
        "user_id": data["user_id"],
        "organization_id": data.get("organization_id"),
        "roadmap_id": data.get("roadmap_id"),
        "task_id": data.get("task_id"),
        "task_title": data.get("task_title", ""),
        "skill_name": data.get("skill_name", ""),
        "activity_type": data.get("activity_type", "TASK"),
        "status": data.get("status", "COMPLETED"),
        "self_reported": bool(data.get("self_reported", True)),
        "evidence_url": data.get("evidence_url", ""),
        "hours": float(data.get("hours", 0)),
        "created_at": now_utc(),
        "completed_at": now_utc() if data.get("status") == "COMPLETED" else None,
    }
    _activity().insert_one(doc)
    return doc


def list_activity(user_id: str, limit: int = 30) -> list:
    return list(_activity().find({"user_id": user_id}).sort("created_at", -1).limit(limit))


def count_completed_activity(user_id: str) -> int:
    return _activity().count_documents({"user_id": user_id, "status": "COMPLETED"})


def upsert_progress(user_id: str, values: dict) -> dict:
    existing = _progress().find_one({"user_id": user_id})
    snapshot = {k: values.get(k) for k in (
        "career_readiness", "roadmap_completion", "skills_verified", "assessments_taken", "average_score"
    )}
    if existing:
        history = existing.get("history", [])
        history.append({**snapshot, "snapshot_at": now_utc()})
        values = dict(values)
        values["history"] = history[-60:]
        values["updated_at"] = now_utc()
        _progress().update_one({"_id": existing["_id"]}, {"$set": values})
        return _progress().find_one({"_id": existing["_id"]})
    doc = {
        "_id": new_id(),
        "user_id": user_id,
        "organization_id": values.get("organization_id"),
        "career_readiness": 0,
        "roadmap_completion": 0,
        "skills_verified": 0,
        "assessments_taken": 0,
        "average_score": 0,
        "history": [{**snapshot, "snapshot_at": now_utc()}],
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    doc.update(values)
    _progress().insert_one(doc)
    return doc


def find_progress(user_id: str) -> dict | None:
    return _progress().find_one({"user_id": user_id})


def list_org_progress(org_id: str) -> list:
    return list(_progress().find({"organization_id": org_id}))


def get_conversation(user_id: str) -> dict | None:
    return _mentor().find_one({"user_id": user_id})


def append_message(user_id: str, org_id: str, message: dict) -> dict:
    existing = get_conversation(user_id)
    if existing:
        _mentor().update_one(
            {"_id": existing["_id"]},
            {"$push": {"messages": message}, "$set": {"updated_at": now_utc()}},
        )
        return get_conversation(user_id)
    doc = {
        "_id": new_id(),
        "user_id": user_id,
        "organization_id": org_id,
        "messages": [message],
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    _mentor().insert_one(doc)
    return doc
