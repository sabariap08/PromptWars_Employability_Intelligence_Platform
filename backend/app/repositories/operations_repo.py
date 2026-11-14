"""Operational collections: notifications, audit, agent runs, provider settings,
trainer assignments and feedback."""
from app.database.mongo import get_db
from app.utils.ids import new_id, now_utc


def _notifications():
    return get_db()["notifications"]


def _audit():
    return get_db()["audit_logs"]


def _executions():
    return get_db()["ai_agent_executions"]


def _providers():
    return get_db()["ai_provider_settings"]


def _feedback():
    return get_db()["trainer_feedback"]


def _assignments():
    return get_db()["trainer_assignments"]


def create_notification(user_id: str, org_id: str | None, title: str, message: str, kind: str = "INFO", link: str = "") -> dict:
    doc = {
        "_id": new_id(),
        "user_id": user_id,
        "organization_id": org_id,
        "title": title,
        "message": message,
        "type": kind,
        "link": link,
        "read": False,
        "created_at": now_utc(),
    }
    _notifications().insert_one(doc)
    return doc


def list_notifications(user_id: str, limit: int = 20) -> list:
    return list(_notifications().find({"user_id": user_id}).sort("created_at", -1).limit(limit))


def mark_read(user_id: str, notification_id: str | None = None) -> int:
    query = {"user_id": user_id}
    if notification_id:
        query["_id"] = notification_id
    result = _notifications().update_many(query, {"$set": {"read": True}})
    return result.modified_count


def unread_count(user_id: str) -> int:
    return _notifications().count_documents({"user_id": user_id, "read": False})


def log_action(actor_id: str, actor_role: str, org_id: str | None, action: str, target_type: str = "", target_id: str = "", detail: str = "", ip: str = "") -> dict:
    doc = {
        "_id": new_id(),
        "actor_id": actor_id,
        "actor_role": actor_role,
        "organization_id": org_id,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "detail": detail,
        "ip": ip,
        "created_at": now_utc(),
    }
    _audit().insert_one(doc)
    return doc


def list_audit(limit: int = 100, org_id: str | None = None) -> list:
    query = {"organization_id": org_id} if org_id else {}
    return list(_audit().find(query).sort("created_at", -1).limit(limit))


def record_execution(data: dict) -> dict:
    doc = {
        "_id": new_id(),
        "workflow": data.get("workflow", ""),
        "agent_name": data.get("agent_name", ""),
        "event": data.get("event", ""),
        "status": data.get("status", "SUCCESS"),
        "provider": data.get("provider", "deterministic"),
        "model": data.get("model", "rules"),
        "user_id": data.get("user_id"),
        "organization_id": data.get("organization_id"),
        "input_summary": data.get("input_summary", ""),
        "output_summary": data.get("output_summary", ""),
        "duration_ms": int(data.get("duration_ms", 0)),
        "error": data.get("error", ""),
        "handoff_to": data.get("handoff_to", ""),
        "created_at": now_utc(),
    }
    _executions().insert_one(doc)
    return doc


def list_executions(limit: int = 60) -> list:
    return list(_executions().find({}).sort("created_at", -1).limit(limit))


def execution_stats() -> dict:
    total = _executions().count_documents({})
    failed = _executions().count_documents({"status": "FAILED"})
    fallback = _executions().count_documents({"provider": "deterministic-fallback"})
    return {"total": total, "failed": failed, "fallback": fallback, "success": total - failed}


def get_provider_settings() -> dict | None:
    return _providers().find_one({"_id": "global"})


def save_provider_settings(data: dict) -> dict:
    _providers().update_one(
        {"_id": "global"},
        {"$set": {**data, "updated_at": now_utc()}},
        upsert=True,
    )
    return get_provider_settings()


def create_assignment(trainer_id: str, learner_id: str, org_id: str, created_by: str) -> dict:
    existing = _assignments().find_one({"trainer_id": trainer_id, "learner_id": learner_id})
    if existing:
        return existing
    doc = {
        "_id": new_id(),
        "trainer_id": trainer_id,
        "learner_id": learner_id,
        "organization_id": org_id,
        "created_by": created_by,
        "created_at": now_utc(),
    }
    _assignments().insert_one(doc)
    return doc


def list_assignments(trainer_id: str) -> list:
    return list(_assignments().find({"trainer_id": trainer_id}))


def create_feedback(data: dict) -> dict:
    doc = {
        "_id": new_id(),
        "trainer_id": data["trainer_id"],
        "learner_id": data["learner_id"],
        "organization_id": data.get("organization_id"),
        "skill_name": data["skill_name"],
        "rating": int(data.get("rating", 3)),
        "feedback": data.get("feedback", ""),
        "created_at": now_utc(),
    }
    _feedback().insert_one(doc)
    return doc


def list_feedback(learner_id: str) -> list:
    return list(_feedback().find({"learner_id": learner_id}).sort("created_at", -1))


def list_trainer_feedback(trainer_id: str) -> list:
    return list(_feedback().find({"trainer_id": trainer_id}).sort("created_at", -1))
