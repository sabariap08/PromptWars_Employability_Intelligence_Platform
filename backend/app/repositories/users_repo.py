"""User document access."""
import re

from app.database.mongo import get_db
from app.utils.ids import new_id, now_utc


def _col():
    return get_db()["users"]


def create_user(data: dict) -> dict:
    doc = {
        "_id": new_id(),
        "full_name": "",
        "email": "",
        "password_hash": "",
        "role": "STUDENT",
        "organization_id": None,
        "department_id": None,
        "phone": "",
        "designation": "",
        "account_status": "EMAIL_VERIFICATION_PENDING",
        "email_verified": False,
        "email_verification_token": None,
        "email_verification_expires_at": None,
        "is_expert": False,
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "approved_at": None,
        "approved_by": None,
        "rejection_reason": None,
    }
    doc.update(data)
    _col().insert_one(doc)
    return doc


def find_by_id(user_id: str) -> dict | None:
    if not user_id:
        return None
    return _col().find_one({"_id": user_id})


def find_by_email(email: str) -> dict | None:
    return _col().find_one({"email": (email or "").lower()})


def find_by_verification_token(token: str) -> dict | None:
    return _col().find_one({"email_verification_token": token})


def update_user(user_id: str, fields: dict) -> dict | None:
    fields = dict(fields)
    fields["updated_at"] = now_utc()
    _col().update_one({"_id": user_id}, {"$set": fields})
    return find_by_id(user_id)


def set_status(user_id: str, status: str, **extra) -> bool:
    fields = {"account_status": status, **extra}
    result = _col().update_one({"_id": user_id}, {"$set": fields})
    return result.modified_count == 1


def transition_status(user_id: str, from_status: str, to_status: str, **extra) -> bool:
    fields = {"account_status": to_status, **extra}
    result = _col().update_one(
        {"_id": user_id, "account_status": from_status}, {"$set": fields}
    )
    return result.modified_count == 1


def list_by_org(org_id: str, roles=None, statuses=None, search: str = "", page: int = 1, page_size: int = 20):
    query = {"organization_id": org_id}
    if roles:
        query["role"] = {"$in": list(roles)}
    if statuses:
        query["account_status"] = {"$in": list(statuses)}
    if search:
        pattern = re.compile(re.escape(search.strip()), re.IGNORECASE)
        query["$or"] = [{"full_name": pattern}, {"email": pattern}]
    total = _col().count_documents(query)
    cursor = (
        _col()
        .find(query)
        .sort("created_at", -1)
        .skip(max(0, (page - 1) * page_size))
        .limit(page_size)
    )
    return list(cursor), total


def list_by_org_department(org_id: str, department_id: str) -> list:
    return list(_col().find({"organization_id": org_id, "department_id": department_id}))


def list_by_role(role: str, status: str | None = None) -> list:
    query = {"role": role}
    if status:
        query["account_status"] = status
    return list(_col().find(query))


def count(query: dict | None = None) -> int:
    return _col().count_documents(query or {})


def count_by_role() -> dict:
    result = {}
    for role in _col().distinct("role"):
        result[role] = _col().count_documents({"role": role})
    return result


def list_all(page: int = 1, page_size: int = 25, search: str = "", role: str = ""):
    query = {}
    if role:
        query["role"] = role
    if search:
        pattern = re.compile(re.escape(search.strip()), re.IGNORECASE)
        query["$or"] = [{"full_name": pattern}, {"email": pattern}]
    total = _col().count_documents(query)
    items = list(
        _col()
        .find(query)
        .sort("created_at", -1)
        .skip(max(0, (page - 1) * page_size))
        .limit(page_size)
    )
    return items, total
