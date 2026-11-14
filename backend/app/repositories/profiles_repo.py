"""Learner profiles, learner skills and evidence access."""
from app.database.mongo import get_db
from app.utils.ids import new_id, now_utc


def _profiles():
    return get_db()["learner_profiles"]


def _skills():
    return get_db()["learner_skills"]


def _evidence():
    return get_db()["skill_evidence"]


def _certs():
    return get_db()["certifications"]


def _projects():
    return get_db()["projects"]


def create_profile(user_id: str, org_id: str, learner_type: str, **extra) -> dict:
    doc = {
        "_id": new_id(),
        "user_id": user_id,
        "organization_id": org_id,
        "learner_type": learner_type,
        "education": {},
        "employment": {},
        "soft_skills": [],
        "interests": [],
        "target_career_id": None,
        "learning_style": "",
        "weekly_hours": 6,
        "onboarding_complete": False,
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    doc.update(extra)
    _profiles().insert_one(doc)
    return doc


def find_profile(user_id: str) -> dict | None:
    return _profiles().find_one({"user_id": user_id})


def list_profiles_for_users(user_ids) -> list:
    ids = set(user_ids)
    if not ids:
        return []
    return [profile for profile in _profiles().find({}) if profile.get("user_id") in ids]


def update_profile(user_id: str, fields: dict) -> dict | None:
    fields = dict(fields)
    fields["updated_at"] = now_utc()
    _profiles().update_one({"user_id": user_id}, {"$set": fields})
    return find_profile(user_id)


def upsert_learner_skill(user_id: str, org_id: str, skill_name: str, values: dict) -> dict:
    existing = _skills().find_one({"user_id": user_id, "skill_name": skill_name})
    if existing:
        values = dict(values)
        values["updated_at"] = now_utc()
        _skills().update_one({"_id": existing["_id"]}, {"$set": values})
        return _skills().find_one({"_id": existing["_id"]})
    doc = {
        "_id": new_id(),
        "user_id": user_id,
        "organization_id": org_id,
        "skill_name": skill_name,
        "skill_id": values.get("skill_id"),
        "self_level": values.get("self_level", ""),
        "proficiency": 0,
        "target_proficiency": values.get("target_proficiency", 60),
        "confidence": "LOW",
        "verification_status": "SELF_REPORTED",
        "evidence_count": 0,
        "breakdown": [],
        "history": [],
        "last_assessed_at": None,
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    doc.update({k: v for k, v in values.items() if k not in doc})
    _skills().insert_one(doc)
    return doc


def find_learner_skill(user_id: str, skill_name: str) -> dict | None:
    return _skills().find_one({"user_id": user_id, "skill_name": skill_name})


def list_learner_skills(user_id: str) -> list:
    return list(_skills().find({"user_id": user_id}).sort("skill_name", 1))


def list_org_skills(org_id: str) -> list:
    return list(_skills().find({"organization_id": org_id}))


def list_skills_for_users(user_ids) -> list:
    ids = set(user_ids)
    if not ids:
        return []
    return [skill for skill in _skills().find({}) if skill.get("user_id") in ids]


def delete_learner_skill(user_id: str, skill_name: str) -> None:
    _skills().delete_one({"user_id": user_id, "skill_name": skill_name})
    _evidence().delete_many({"user_id": user_id, "skill_name": skill_name})


def save_learner_skill(user_skill: dict) -> None:
    _skills().replace_one({"_id": user_skill["_id"]}, user_skill)


def add_evidence(data: dict) -> dict:
    doc = {
        "_id": new_id(),
        "user_id": data["user_id"],
        "organization_id": data.get("organization_id"),
        "skill_name": data["skill_name"],
        "source_type": data["source_type"],
        "source_id": data.get("source_id"),
        "title": data.get("title", ""),
        "score": float(data.get("score", 0)),
        "verified": bool(data.get("verified", False)),
        "notes": data.get("notes", ""),
        "created_at": now_utc(),
    }
    _evidence().insert_one(doc)
    return doc


def list_evidence(user_id: str, skill_name: str | None = None) -> list:
    query = {"user_id": user_id}
    if skill_name:
        query["skill_name"] = skill_name
    return list(_evidence().find(query).sort("created_at", -1))


def count_evidence(user_id: str, skill_name: str) -> int:
    return _evidence().count_documents({"user_id": user_id, "skill_name": skill_name})


def add_certification(data: dict) -> dict:
    doc = {
        "_id": new_id(),
        "user_id": data["user_id"],
        "organization_id": data.get("organization_id"),
        "name": data["name"],
        "issuer": data.get("issuer", ""),
        "issued_on": data.get("issued_on", ""),
        "skills": data.get("skills", []),
        "file_name": data.get("file_name", ""),
        "file_path": data.get("file_path", ""),
        "status": "PENDING_VERIFICATION",
        "assessment_id": None,
        "score": None,
        "created_at": now_utc(),
        "verified_at": None,
    }
    _certs().insert_one(doc)
    return doc


def find_certification(cert_id: str, user_id: str | None = None) -> dict | None:
    query = {"_id": cert_id}
    if user_id:
        query["user_id"] = user_id
    return _certs().find_one(query)


def list_certifications(user_id: str) -> list:
    return list(_certs().find({"user_id": user_id}).sort("created_at", -1))


def update_certification(cert_id: str, fields: dict) -> dict | None:
    _certs().update_one({"_id": cert_id}, {"$set": fields})
    return _certs().find_one({"_id": cert_id})


def add_project(data: dict) -> dict:
    doc = {
        "_id": new_id(),
        "user_id": data["user_id"],
        "organization_id": data.get("organization_id"),
        "name": data["name"],
        "description": data.get("description", ""),
        "technologies": data.get("technologies", []),
        "repo_url": data.get("repo_url", ""),
        "skills": data.get("skills", []),
        "status": "PENDING_VERIFICATION",
        "ai_analysis": {},
        "expert_feedback": "",
        "created_at": now_utc(),
        "verified_at": None,
    }
    _projects().insert_one(doc)
    return doc


def find_project(project_id: str, user_id: str | None = None) -> dict | None:
    query = {"_id": project_id}
    if user_id:
        query["user_id"] = user_id
    return _projects().find_one(query)


def list_projects(user_id: str) -> list:
    return list(_projects().find({"user_id": user_id}).sort("created_at", -1))


def update_project(project_id: str, fields: dict) -> dict | None:
    _projects().update_one({"_id": project_id}, {"$set": fields})
    return _projects().find_one({"_id": project_id})


def count_learner_profiles() -> int:
    return _profiles().count_documents({})
