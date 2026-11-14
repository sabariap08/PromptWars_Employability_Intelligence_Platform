"""Learner profile management, secure uploads and evidence submissions."""
import os

from flask import current_app

from app.repositories import catalog_repo, profiles_repo
from app.services import ops_service, skill_service
from app.utils.ids import new_id
from app.utils.responses import AppError
from app.utils.text import clean_text, is_http_url, safe_filename
from app.validators.common import require_fields

ALLOWED_UPLOAD_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
MAX_SKILLS_PER_PROFILE = 40


def _upload_root() -> str:
    root = current_app.config["UPLOAD_DIR"]
    os.makedirs(root, exist_ok=True)
    return root


def save_secure_upload(file_storage, user_id: str) -> dict:
    if not file_storage or not file_storage.filename:
        return {"file_name": "", "file_path": ""}
    filename = safe_filename(file_storage.filename)
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise AppError(
            "Only PDF, PNG or JPG files can be uploaded.",
            "INVALID_FILE_TYPE",
            422,
            {"allowed": sorted(ALLOWED_UPLOAD_EXTENSIONS)},
        )
    user_dir = os.path.join(_upload_root(), user_id)
    os.makedirs(user_dir, exist_ok=True)
    stored_name = f"{new_id()}_{filename}"
    path = os.path.join(user_dir, stored_name)
    file_storage.save(path)
    return {"file_name": filename, "file_path": path}


def profile_completeness(user: dict, profile: dict | None, skill_count: int) -> int:
    checks = [
        bool(user.get("phone")),
        bool(user.get("department_id")),
        bool(profile),
        bool(profile and (profile.get("education") or profile.get("employment"))),
        skill_count > 0,
        bool(profile and profile.get("soft_skills")),
        bool(profile and profile.get("target_career_id")),
        bool(profile and profile.get("learning_style")),
        bool(profile and profile.get("weekly_hours")),
    ]
    return round(sum(1 for check in checks if check) / len(checks) * 100)


def get_profile(user: dict) -> dict:
    profile = profiles_repo.find_profile(user["_id"])
    if not profile:
        profile = profiles_repo.create_profile(
            user["_id"], user.get("organization_id"), user.get("role", "STUDENT")
        )
    return profile


def save_profile(user: dict, payload: dict) -> dict:
    profile = get_profile(user)
    org_id = user.get("organization_id")

    target_career_id = payload.get("target_career_id") or profile.get("target_career_id")
    if target_career_id:
        role = catalog_repo.find_career(target_career_id)
        if not role or not role.get("is_active"):
            raise AppError("Please choose a valid career goal.", "CAREER_NOT_FOUND", 422)

    skills = payload.get("skills") or []
    if not isinstance(skills, list):
        raise AppError("Skills must be a list.", "INVALID_SKILLS", 422)
    if len(skills) > MAX_SKILLS_PER_PROFILE:
        raise AppError("Please list at most 40 skills.", "TOO_MANY_SKILLS", 422)
    added = []
    for item in skills:
        if isinstance(item, dict):
            name = clean_text(item.get("name"), 80)
            level = clean_text(item.get("level"), 20).upper() or "BEGINNER"
        else:
            name = clean_text(item, 80)
            level = "BEGINNER"
        if name:
            skill_service.add_self_skill(user["_id"], org_id, name, level)
            added.append(name)

    soft_skills = payload.get("soft_skills")
    if isinstance(soft_skills, list):
        soft_skills = [clean_text(s, 60) for s in soft_skills if clean_text(s, 60)][:15]
        for name in soft_skills:
            skill_service.add_self_skill(user["_id"], org_id, name, "INTERMEDIATE")
    else:
        soft_skills = profile.get("soft_skills", [])

    weekly_hours = payload.get("weekly_hours", profile.get("weekly_hours", 6))
    try:
        weekly_hours = max(1, min(40, int(weekly_hours)))
    except (TypeError, ValueError):
        weekly_hours = 6

    education = dict(profile.get("education") or {})
    if isinstance(payload.get("education"), dict):
        education.update({k: clean_text(v, 150) for k, v in payload["education"].items()})
    employment = dict(profile.get("employment") or {})
    if isinstance(payload.get("employment"), dict):
        employment.update({k: clean_text(v, 150) for k, v in payload["employment"].items()})

    interests = payload.get("interests", profile.get("interests", []))
    if isinstance(interests, list):
        interests = [clean_text(i, 80) for i in interests if clean_text(i, 80)][:15]

    fields = {
        "education": education,
        "employment": employment,
        "soft_skills": soft_skills,
        "interests": interests,
        "target_career_id": target_career_id,
        "learning_style": clean_text(payload.get("learning_style"), 80) or profile.get("learning_style", ""),
        "weekly_hours": weekly_hours,
    }
    skill_count = len(profiles_repo.list_learner_skills(user["_id"]))
    fields["onboarding_complete"] = bool(fields["target_career_id"] and skill_count > 0)
    if isinstance(payload.get("phone"), str) and payload["phone"].strip():
        from app.repositories import users_repo

        users_repo.update_user(user["_id"], {"phone": clean_text(payload["phone"], 40)})

    updated = profiles_repo.update_profile(user["_id"], fields)
    ops_service.audit("PROFILE_UPDATED", "learner_profile", updated["_id"])
    return updated


def add_certification(user: dict, payload: dict, file_storage=None) -> dict:
    require_fields(payload, ["name", "issuer"])
    skills = payload.get("skills") or []
    if not isinstance(skills, list) or not [s for s in skills if clean_text(s)]:
        raise AppError("Add at least one skill this certification demonstrates.", "SKILLS_REQUIRED", 422)
    skills = [clean_text(s, 80) for s in skills if clean_text(s, 80)][:10]
    upload = save_secure_upload(file_storage, user["_id"])
    cert = profiles_repo.add_certification(
        {
            "user_id": user["_id"],
            "organization_id": user.get("organization_id"),
            "name": clean_text(payload["name"], 150),
            "issuer": clean_text(payload["issuer"], 150),
            "issued_on": clean_text(payload.get("issued_on"), 40),
            "skills": skills,
            **upload,
        }
    )
    ops_service.audit("CERTIFICATION_SUBMITTED", "certification", cert["_id"], cert["name"])
    return cert


def add_project(user: dict, payload: dict) -> dict:
    require_fields(payload, ["name", "description"])
    description = clean_text(payload["description"], 3000)
    if len(description) < 40:
        raise AppError(
            "Please describe the project in at least 40 characters.",
            "DESCRIPTION_TOO_SHORT",
            422,
            {"field": "description"},
        )
    repo_url = clean_text(payload.get("repo_url"), 400)
    if repo_url and not is_http_url(repo_url):
        raise AppError("Repository link must start with http:// or https://.", "INVALID_URL", 422)
    technologies = payload.get("technologies") or []
    if isinstance(technologies, str):
        technologies = [t.strip() for t in technologies.split(",") if t.strip()]
    technologies = [clean_text(t, 60) for t in technologies if clean_text(t, 60)][:20]
    skills = payload.get("skills") or technologies
    skills = [clean_text(s, 80) for s in skills if clean_text(s, 80)][:15]

    project = profiles_repo.add_project(
        {
            "user_id": user["_id"],
            "organization_id": user.get("organization_id"),
            "name": clean_text(payload["name"], 150),
            "description": description,
            "technologies": technologies,
            "repo_url": repo_url,
            "skills": skills,
        }
    )
    ops_service.audit("PROJECT_SUBMITTED", "project", project["_id"], project["name"])
    return project


def get_bundle(user: dict) -> dict:
    profile = get_profile(user)
    skills = profiles_repo.list_learner_skills(user["_id"])
    completeness = profile_completeness(user, profile, len(skills))
    target_career = catalog_repo.find_career(profile.get("target_career_id")) if profile.get("target_career_id") else None
    return {
        "user": {k: v for k, v in user.items() if k != "password_hash"},
        "profile": profile,
        "skills": skills,
        "certifications": profiles_repo.list_certifications(user["_id"]),
        "projects": profiles_repo.list_projects(user["_id"]),
        "evidence": profiles_repo.list_evidence(user["_id"]),
        "target_career": target_career,
        "completeness": completeness,
    }
