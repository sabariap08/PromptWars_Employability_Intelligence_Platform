"""Course catalog, enrollments and module progress."""
import re

from app.database.mongo import get_db
from app.utils.ids import new_id, now_utc


def _courses():
    return get_db()["courses"]


def _enrollments():
    return get_db()["course_enrollments"]


def _modules(raw_modules) -> list:
    modules = []
    for index, item in enumerate(raw_modules or []):
        if isinstance(item, dict):
            title = str(item.get("title") or "").strip()
            module_id = str(item.get("id") or item.get("_id") or "").strip()
        else:
            title = str(item or "").strip()
            module_id = ""
        if not title:
            continue
        modules.append(
            {
                "id": module_id or new_id(),
                "title": title[:180],
                "position": index + 1,
            }
        )
    return modules


def create_course(data: dict) -> dict:
    modules = _modules(data.get("modules"))
    doc = {
        "_id": new_id(),
        "title": data["title"],
        "provider": data.get("provider", ""),
        "description": data.get("description", ""),
        "url": data.get("url", ""),
        "difficulty": data.get("difficulty", "BEGINNER"),
        "duration_hours": float(data.get("duration_hours", 6)),
        "skill_names": data.get("skill_names", []),
        "modules": modules,
        "is_active": bool(data.get("is_active", True)),
        "created_by": data.get("created_by"),
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    _courses().insert_one(doc)
    return doc


def list_courses(search: str = "", skill: str = "", difficulty: str = "", active_only: bool = True, limit: int = 200) -> list:
    query = {}
    if active_only:
        query["is_active"] = True
    if skill:
        query["skill_names"] = skill
    if difficulty:
        query["difficulty"] = difficulty.upper()
    if search:
        pattern = re.compile(re.escape(search.strip()), re.IGNORECASE)
        query["$or"] = [{"title": pattern}, {"provider": pattern}, {"description": pattern}]
    return list(_courses().find(query).sort("title", 1).limit(limit))


def find_course(course_id: str, active_only: bool = False) -> dict | None:
    query = {"_id": course_id}
    if active_only:
        query["is_active"] = True
    return _courses().find_one(query)


def update_course(course_id: str, fields: dict) -> dict | None:
    allowed = {
        "title", "provider", "description", "url", "difficulty",
        "duration_hours", "skill_names", "modules", "is_active",
    }
    update = {key: value for key, value in fields.items() if key in allowed}
    if "modules" in update:
        update["modules"] = _modules(update["modules"])
    if "skill_names" in update and isinstance(update["skill_names"], str):
        update["skill_names"] = [item.strip() for item in update["skill_names"].split(",") if item.strip()]
    if not update:
        return find_course(course_id)
    update["updated_at"] = now_utc()
    _courses().update_one({"_id": course_id}, {"$set": update})
    return find_course(course_id)


def count_courses(active_only: bool = True) -> int:
    return _courses().count_documents({"is_active": True} if active_only else {})


def create_enrollment(user: dict, course: dict) -> dict:
    doc = {
        "_id": new_id(),
        "user_id": user["_id"],
        "organization_id": user.get("organization_id"),
        "course_id": course["_id"],
        "status": "ENROLLED",
        "completed_module_ids": [],
        "progress": 0,
        "started_at": None,
        "completed_at": None,
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    _enrollments().insert_one(doc)
    return doc


def find_enrollment(enrollment_id: str, user_id: str | None = None) -> dict | None:
    query = {"_id": enrollment_id}
    if user_id:
        query["user_id"] = user_id
    return _enrollments().find_one(query)


def find_enrollment_for_course(user_id: str, course_id: str) -> dict | None:
    return _enrollments().find_one({"user_id": user_id, "course_id": course_id})


def list_enrollments(user_id: str) -> list:
    return list(_enrollments().find({"user_id": user_id}).sort("created_at", -1))


def list_org_enrollments(org_id: str) -> list:
    return list(_enrollments().find({"organization_id": org_id}))


def update_enrollment(enrollment_id: str, fields: dict) -> dict | None:
    fields = dict(fields)
    fields["updated_at"] = now_utc()
    _enrollments().update_one({"_id": enrollment_id}, {"$set": fields})
    return find_enrollment(enrollment_id)


def count_completed(user_id: str) -> int:
    return _enrollments().count_documents({"user_id": user_id, "status": "COMPLETED"})


def list_enrollments_for_users(user_ids) -> list:
    ids = set(user_ids)
    if not ids:
        return []
    return [row for row in _enrollments().find({}) if row.get("user_id") in ids]
