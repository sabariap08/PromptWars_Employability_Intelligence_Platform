"""Skill taxonomy, career roles, learning resources and question bank."""
import re

from app.database.mongo import get_db
from app.utils.ids import new_id, now_utc


def _skills():
    return get_db()["skills"]


def _careers():
    return get_db()["career_roles"]


def _resources():
    return get_db()["learning_resources"]


def _questions():
    return get_db()["assessment_questions"]


def upsert_skill(name: str, category: str = "", description: str = "") -> dict:
    existing = _skills().find_one({"name": name})
    if existing:
        return existing
    doc = {
        "_id": new_id(),
        "name": name,
        "category": category,
        "description": description,
        "created_at": now_utc(),
    }
    _skills().insert_one(doc)
    return doc


def list_skills() -> list:
    return list(_skills().find({}).sort("name", 1))


def find_skill_by_name(name: str) -> dict | None:
    return _skills().find_one({"name": name})


def create_career(data: dict) -> dict:
    doc = {
        "_id": new_id(),
        "name": data["name"],
        "description": data.get("description", ""),
        "experience_level": data.get("experience_level", "Entry level"),
        "required_skills": data.get("required_skills", []),
        "preferred_skills": data.get("preferred_skills", []),
        "certifications": data.get("certifications", []),
        "project_expectations": data.get("project_expectations", ""),
        "milestones": data.get("milestones", []),
        "is_active": True,
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    _careers().insert_one(doc)
    return doc


def list_careers(active_only: bool = True) -> list:
    query = {"is_active": True} if active_only else {}
    return list(_careers().find(query).sort("name", 1))


def find_career(career_id: str) -> dict | None:
    if not career_id:
        return None
    return _careers().find_one({"_id": career_id})


def find_career_by_name(name: str) -> dict | None:
    return _careers().find_one({"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}})


def update_career(career_id: str, fields: dict) -> dict | None:
    fields = dict(fields)
    fields["updated_at"] = now_utc()
    _careers().update_one({"_id": career_id}, {"$set": fields})
    return find_career(career_id)


def create_resource(data: dict) -> dict:
    doc = {
        "_id": new_id(),
        "title": data["title"],
        "provider": data.get("provider", ""),
        "url": data["url"],
        "resource_type": data.get("resource_type", "TUTORIAL"),
        "skill_names": data.get("skill_names", []),
        "difficulty": data.get("difficulty", "BEGINNER"),
        "duration_hours": float(data.get("duration_hours", 4)),
        "description": data.get("description", ""),
        "is_trusted": bool(data.get("is_trusted", True)),
        "created_by": data.get("created_by"),
        "created_at": now_utc(),
    }
    _resources().insert_one(doc)
    return doc


def list_resources(skill_name: str | None = None, limit: int = 200) -> list:
    query = {"skill_names": skill_name} if skill_name else {}
    return list(_resources().find(query).sort("title", 1).limit(limit))


def find_resource(resource_id: str) -> dict | None:
    return _resources().find_one({"_id": resource_id})


def find_resources_for_skill(skill_name: str) -> list:
    return list(_resources().find({"skill_names": skill_name}).sort("duration_hours", 1))


def create_question(data: dict) -> dict:
    doc = {
        "_id": new_id(),
        "skill_name": data["skill_name"],
        "difficulty": data.get("difficulty", "EASY").upper(),
        "question_type": data.get("question_type", "FACTUAL").upper(),
        "prompt": data["prompt"],
        "options": data.get("options", []),
        "correct_option": data.get("correct_option", "A"),
        "correct_keywords": data.get("correct_keywords", []),
        "explanation": data.get("explanation", ""),
        "points": int(data.get("points", 1)),
        "created_at": now_utc(),
    }
    _questions().insert_one(doc)
    return doc


def list_questions_for_skills(skill_names: list) -> list:
    return list(_questions().find({"skill_name": {"$in": list(skill_names)}}))


def find_questions_by_ids(question_ids: list) -> list:
    return list(_questions().find({"_id": {"$in": list(question_ids)}}))


def count_questions() -> int:
    return _questions().count_documents({})
