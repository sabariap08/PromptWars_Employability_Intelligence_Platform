"""Organization affiliation-change requests."""
import re

from app.database.mongo import get_db
from app.utils.ids import new_id, now_utc


def _col():
    return get_db()["affiliation_requests"]


def create_request(data: dict) -> dict:
    doc = {
        "_id": new_id(),
        "user_id": data["user_id"],
        "current_organization_id": data["current_organization_id"],
        "requested_organization_id": data["requested_organization_id"],
        "requested_department_id": data.get("requested_department_id"),
        "reason": data.get("reason", ""),
        "status": "PENDING",
        "created_at": now_utc(),
        "reviewed_at": None,
        "reviewed_by": None,
        "reviewer_note": "",
    }
    _col().insert_one(doc)
    return doc


def find_request(request_id: str) -> dict | None:
    return _col().find_one({"_id": request_id})


def find_pending_for_user(user_id: str) -> dict | None:
    return _col().find_one({"user_id": user_id, "status": "PENDING"})


def list_for_user(user_id: str, limit: int = 20) -> list:
    return list(_col().find({"user_id": user_id}).sort("created_at", -1).limit(limit))


def list_for_organization(org_id: str | None, status: str = "", search: str = "", limit: int = 100) -> list:
    query = {}
    if org_id:
        query["$or"] = [
            {"current_organization_id": org_id},
            {"requested_organization_id": org_id},
        ]
    if status:
        query["status"] = status
    if search:
        pattern = re.compile(re.escape(search.strip()), re.IGNORECASE)
        query["reason"] = pattern
    return list(_col().find(query).sort("created_at", -1).limit(limit))


def resolve(request_id: str, status: str, reviewer_id: str, note: str = "") -> bool:
    result = _col().update_one(
        {"_id": request_id, "status": "PENDING"},
        {
            "$set": {
                "status": status,
                "reviewed_at": now_utc(),
                "reviewed_by": reviewer_id,
                "reviewer_note": note,
            }
        },
    )
    return result.modified_count == 1


def count_pending(org_id: str | None = None) -> int:
    query = {"status": "PENDING"}
    if org_id:
        query["$or"] = [
            {"current_organization_id": org_id},
            {"requested_organization_id": org_id},
        ]
    return _col().count_documents(query)
