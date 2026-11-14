"""Organizations, departments and approval request access."""
import re

from app.database.mongo import get_db
from app.utils.ids import new_id, now_utc


def _orgs():
    return get_db()["organizations"]


def _departments():
    return get_db()["departments"]


def _approvals():
    return get_db()["approval_requests"]


def create_org(data: dict) -> dict:
    doc = {
        "_id": new_id(),
        "name": "",
        "organization_type": "UNIVERSITY",
        "subtype": "",
        "industry": "",
        "location": {"country": "", "state": "", "district": "", "city": ""},
        "official_email": "",
        "website": "",
        "contact_number": "",
        "address": "",
        "registration_identifier": "",
        "verification_documents": [],
        "approval_status": "PENDING_APPROVAL",
        "created_at": now_utc(),
        "updated_at": now_utc(),
        "approved_at": None,
        "approved_by": None,
        "rejection_reason": None,
    }
    doc.update(data)
    _orgs().insert_one(doc)
    return doc


def find_org(org_id: str) -> dict | None:
    if not org_id:
        return None
    return _orgs().find_one({"_id": org_id})


def find_org_by_name(name: str) -> dict | None:
    return _orgs().find_one({"name": {"$regex": f"^{re.escape((name or '').strip())}$", "$options": "i"}})


def find_org_by_identifier(identifier: str) -> dict | None:
    if not identifier:
        return None
    return _orgs().find_one({"registration_identifier": identifier.strip()})


def update_org(org_id: str, fields: dict) -> dict | None:
    fields = dict(fields)
    fields["updated_at"] = now_utc()
    _orgs().update_one({"_id": org_id}, {"$set": fields})
    return find_org(org_id)


def transition_org(org_id: str, from_status: str, to_status: str, **extra) -> bool:
    fields = {"approval_status": to_status, "updated_at": now_utc(), **extra}
    result = _orgs().update_one(
        {"_id": org_id, "approval_status": from_status}, {"$set": fields}
    )
    return result.modified_count == 1


def search_approved(query_text: str, org_type: str, limit: int = 10) -> list:
    pattern = re.compile(re.escape((query_text or "").strip()), re.IGNORECASE)
    query = {
        "organization_type": org_type,
        "approval_status": "APPROVED",
        "$or": [
            {"name": pattern},
            {"location.city": pattern},
            {"location.state": pattern},
        ],
    }
    return list(_orgs().find(query).sort("name", 1).limit(limit))


def list_orgs(status: str = "", org_type: str = "", search: str = "", page: int = 1, page_size: int = 20):
    query = {}
    if status:
        query["approval_status"] = status
    if org_type:
        query["organization_type"] = org_type
    if search:
        pattern = re.compile(re.escape(search.strip()), re.IGNORECASE)
        query["$or"] = [{"name": pattern}, {"official_email": pattern}, {"location.city": pattern}]
    total = _orgs().count_documents(query)
    items = list(
        _orgs()
        .find(query)
        .sort("created_at", -1)
        .skip(max(0, (page - 1) * page_size))
        .limit(page_size)
    )
    return items, total


def count_orgs(query: dict | None = None) -> int:
    return _orgs().count_documents(query or {})


def count_by_status() -> dict:
    result = {}
    for status in _orgs().distinct("approval_status"):
        result[status] = _orgs().count_documents({"approval_status": status})
    return result


def create_department(org_id: str, name: str, code: str = "") -> dict:
    doc = {
        "_id": new_id(),
        "organization_id": org_id,
        "name": name,
        "code": code,
        "status": "ACTIVE",
        "created_at": now_utc(),
    }
    _departments().insert_one(doc)
    return doc


def find_department(department_id: str) -> dict | None:
    if not department_id:
        return None
    return _departments().find_one({"_id": department_id})


def list_departments(org_id: str) -> list:
    return list(_departments().find({"organization_id": org_id}).sort("name", 1))


def list_all_departments() -> list:
    return list(_departments().find({}).sort("name", 1))


def create_approval_request(data: dict) -> dict:
    doc = {
        "_id": new_id(),
        "request_type": "MEMBERSHIP",
        "applicant_user_id": None,
        "organization_id": None,
        "requested_role": "",
        "assigned_approver_role": "",
        "status": "PENDING",
        "remarks": "",
        "created_at": now_utc(),
        "reviewed_at": None,
        "reviewed_by": None,
    }
    doc.update(data)
    _approvals().insert_one(doc)
    return doc


def find_request_by_applicant(user_id: str, request_type: str) -> dict | None:
    return _approvals().find_one({"applicant_user_id": user_id, "request_type": request_type})


def find_request_by_org(org_id: str, request_type: str) -> dict | None:
    return _approvals().find_one({"organization_id": org_id, "request_type": request_type})


def update_request(request_id: str, fields: dict) -> None:
    _approvals().update_one({"_id": request_id}, {"$set": fields})


def resolve_request_for_org(org_id: str, request_type: str, status: str, reviewer_id: str, remarks: str = "") -> bool:
    result = _approvals().update_one(
        {"organization_id": org_id, "request_type": request_type, "status": "PENDING"},
        {
            "$set": {
                "status": status,
                "reviewed_at": now_utc(),
                "reviewed_by": reviewer_id,
                "remarks": remarks,
            }
        },
    )
    return result.modified_count >= 1


def resolve_request_for_user(user_id: str, request_type: str, status: str, reviewer_id: str, remarks: str = "") -> bool:
    result = _approvals().update_one(
        {"applicant_user_id": user_id, "request_type": request_type, "status": "PENDING"},
        {
            "$set": {
                "status": status,
                "reviewed_at": now_utc(),
                "reviewed_by": reviewer_id,
                "remarks": remarks,
            }
        },
    )
    return result.modified_count >= 1
