"""Platform administration: overview, catalog, providers, agents and audit."""
from flask import Blueprint, current_app

from app.ai_providers.provider_manager import PROVIDER_CLASSES, build_provider_manager
from app.api.common import arg, json_body, pagination
from app.orchestration.orchestrator import AGENTS
from app.orchestration.workflow_registry import WORKFLOWS
from app.repositories import (
    catalog_repo,
    courses_repo,
    operations_repo,
    organizations_repo,
    users_repo,
)
from app.security.auth import (
    ADMIN_ROLES,
    ROLE_ORGANIZATION_ADMIN,
    ROLE_SUPER_ADMIN,
    ROLE_UNIVERSITY_ADMIN,
    api_roles_required,
    current_user,
)
from app.services import analytics_service
from app.utils.responses import AppError, ok

bp = Blueprint("admin_api", __name__, url_prefix="/api/admin")


@bp.get("/overview")
@api_roles_required(ROLE_SUPER_ADMIN)
def overview():
    return ok(analytics_service.platform_overview())


@bp.get("/organizations")
@api_roles_required(ROLE_SUPER_ADMIN)
def organizations():
    page = pagination()
    items, total = organizations_repo.list_orgs(
        status=arg("status"),
        org_type=arg("type"),
        search=arg("q"),
        page=page["page"],
        page_size=page["page_size"],
    )
    return ok({"organizations": items, "total": total, "page": page["page"], "page_size": page["page_size"]})


@bp.get("/users")
@api_roles_required(ROLE_SUPER_ADMIN)
def users():
    page = pagination()
    items, total = users_repo.list_all(
        page=page["page"], page_size=page["page_size"], search=arg("q"), role=arg("role")
    )
    clean = [{k: v for k, v in item.items() if k not in {"password_hash", "email_verification_token"}} for item in items]
    return ok({"users": clean, "total": total, "page": page["page"], "page_size": page["page_size"]})


@bp.get("/executions")
@api_roles_required(ROLE_SUPER_ADMIN)
def executions():
    try:
        limit = max(1, min(200, int(arg("limit", "60") or 60)))
    except ValueError:
        limit = 60
    return ok({"executions": operations_repo.list_executions(limit=limit), "stats": operations_repo.execution_stats()})


@bp.get("/agents")
@api_roles_required(ROLE_SUPER_ADMIN)
def agents():
    return ok(
        {
            "agents": [
                {"name": cls.name, "label": cls.label, "key": key}
                for key, cls in AGENTS.items()
            ],
            "workflows": WORKFLOWS,
        }
    )


@bp.get("/audit")
@api_roles_required(*ADMIN_ROLES)
def audit():
    actor = current_user()
    try:
        limit = max(1, min(300, int(arg("limit", "100") or 100)))
    except ValueError:
        limit = 100
    if actor["role"] == ROLE_SUPER_ADMIN:
        org_id = arg("org_id") or None
    else:
        org_id = actor.get("organization_id")
    return ok({"logs": operations_repo.list_audit(limit=limit, org_id=org_id)})


@bp.get("/providers")
@api_roles_required(ROLE_SUPER_ADMIN)
def providers():
    manager = current_app.extensions.get("ai_manager")
    settings = operations_repo.get_provider_settings() or {}
    return ok(
        {
            "providers": manager.status() if manager else [],
            "settings": {
                "primary_provider": settings.get("primary_provider", ""),
                "fallback_order": settings.get("fallback_order", ""),
                "updated_at": settings.get("updated_at"),
            },
            "order": manager.order if manager else [],
        }
    )


@bp.put("/providers")
@api_roles_required(ROLE_SUPER_ADMIN)
def save_providers():
    data = json_body()
    primary = (data.get("primary_provider") or "").strip().lower()
    fallback_raw = data.get("fallback_order") or ""
    if isinstance(fallback_raw, list):
        fallback = [str(item).strip().lower() for item in fallback_raw if str(item).strip()]
    else:
        fallback = [item.strip().lower() for item in str(fallback_raw).split(",") if item.strip()]
    unknown = [name for name in ([primary] if primary else []) + fallback if name not in PROVIDER_CLASSES]
    if unknown:
        raise AppError(
            "Unknown AI provider selected.",
            "INVALID_PROVIDER",
            422,
            {"unknown": unknown, "available": sorted(PROVIDER_CLASSES)},
        )
    operations_repo.save_provider_settings(
        {"primary_provider": primary, "fallback_order": ",".join(fallback)}
    )
    app = current_app._get_current_object()
    settings = operations_repo.get_provider_settings() or {}
    app.extensions["ai_manager"] = build_provider_manager(
        app,
        {
            "primary_provider": settings.get("primary_provider"),
            "fallback_order": settings.get("fallback_order"),
        },
    )
    manager = app.extensions["ai_manager"]
    return ok(
        {"providers": manager.status(), "order": manager.order},
        "AI provider routing updated.",
    )


@bp.get("/catalog")
@api_roles_required(ROLE_SUPER_ADMIN)
def catalog():
    careers = catalog_repo.list_careers(active_only=False)
    resources = catalog_repo.list_resources(limit=200)
    return ok(
        {
            "skills": catalog_repo.list_skills(),
            "careers": careers,
            "resources": resources,
            "counts": {
                "skills": len(catalog_repo.list_skills()),
                "careers": len(careers),
                "resources": len(resources),
                "questions": catalog_repo.count_questions(),
                "courses": courses_repo.count_courses(active_only=False),
            },
        }
    )


@bp.post("/catalog/skills")
@api_roles_required(ROLE_SUPER_ADMIN)
def create_skill():
    data = json_body()
    name = (data.get("name") or "").strip()
    if not name:
        raise AppError("Skill name is required.", "VALIDATION_ERROR", 422)
    skill = catalog_repo.upsert_skill(name[:80], (data.get("category") or "")[:80], (data.get("description") or "")[:500])
    return ok(skill, "Skill saved.", 201)


def _skill_rows(raw, default_min=60.0, default_weight=2.0) -> list:
    rows = []
    for item in raw or []:
        if isinstance(item, str):
            name, minimum, weight = item.strip(), default_min, default_weight
        elif isinstance(item, dict):
            name = (item.get("skill_name") or item.get("name") or "").strip()
            try:
                minimum = float(item.get("min_proficiency", default_min))
            except (TypeError, ValueError):
                minimum = default_min
            try:
                weight = float(item.get("weight", default_weight))
            except (TypeError, ValueError):
                weight = default_weight
        else:
            continue
        if not name:
            continue
        skill = catalog_repo.upsert_skill(name)
        rows.append(
            {
                "skill_id": skill["_id"],
                "skill_name": name,
                "min_proficiency": max(0.0, min(100.0, minimum)),
                "weight": max(0.1, min(10.0, weight)),
            }
        )
    return rows


@bp.post("/catalog/careers")
@api_roles_required(ROLE_SUPER_ADMIN)
def create_career():
    data = json_body()
    name = (data.get("name") or "").strip()
    if not name:
        raise AppError("Career name is required.", "VALIDATION_ERROR", 422)
    if catalog_repo.find_career_by_name(name):
        raise AppError("A career with this name already exists.", "CAREER_EXISTS", 409)
    career = catalog_repo.create_career(
        {
            "name": name[:120],
            "description": (data.get("description") or "")[:1000],
            "experience_level": (data.get("experience_level") or "Entry level")[:80],
            "required_skills": _skill_rows(data.get("required_skills")),
            "preferred_skills": _skill_rows(data.get("preferred_skills"), 50.0, 1.0),
            "certifications": data.get("certifications") or [],
            "project_expectations": (data.get("project_expectations") or "")[:1000],
            "milestones": data.get("milestones") or [],
        }
    )
    return ok(career, "Career created.", 201)


@bp.post("/catalog/resources")
@api_roles_required(ROLE_SUPER_ADMIN)
def create_resource():
    data = json_body()
    title = (data.get("title") or "").strip()
    url = (data.get("url") or "").strip()
    if not title or not url:
        raise AppError("Title and URL are required.", "VALIDATION_ERROR", 422)
    from app.utils.text import is_http_url

    if not is_http_url(url):
        raise AppError("URL must start with http:// or https://.", "INVALID_URL", 422)
    skills = data.get("skill_names") or []
    if isinstance(skills, str):
        skills = [item.strip() for item in skills.split(",") if item.strip()]
    for skill_name in skills:
        if skill_name:
            catalog_repo.upsert_skill(skill_name)
    resource = catalog_repo.create_resource(
        {
            "title": title[:160],
            "provider": (data.get("provider") or "")[:120],
            "url": url[:400],
            "resource_type": (data.get("resource_type") or "TUTORIAL").upper(),
            "skill_names": skills,
            "difficulty": (data.get("difficulty") or "BEGINNER").upper(),
            "duration_hours": data.get("duration_hours", 4),
            "description": (data.get("description") or "")[:1000],
            "created_by": current_user()["_id"],
        }
    )
    return ok(resource, "Learning resource created.", 201)


@bp.post("/catalog/questions")
@api_roles_required(*ADMIN_ROLES)
def create_question():
    data = json_body()
    skill_name = (data.get("skill_name") or "").strip()
    prompt = (data.get("prompt") or "").strip()
    if not skill_name or not prompt:
        raise AppError("Skill and prompt are required.", "VALIDATION_ERROR", 422)
    question_type = (data.get("question_type") or "FACTUAL").upper()
    options = data.get("options") or []
    if isinstance(options, str):
        options = [item.strip() for item in options.split("|") if item.strip()]
    catalog_repo.upsert_skill(skill_name)
    question = catalog_repo.create_question(
        {
            "skill_name": skill_name[:80],
            "difficulty": (data.get("difficulty") or "EASY").upper(),
            "question_type": question_type,
            "prompt": prompt[:1000],
            "options": options,
            "correct_option": data.get("correct_option", "A"),
            "correct_keywords": data.get("correct_keywords") or [],
            "explanation": (data.get("explanation") or "")[:1000],
            "points": data.get("points", 2 if question_type != "FACTUAL" else 1),
        }
    )
    return ok(question, "Question created.", 201)


def _course_payload(data: dict) -> dict:
    title = (data.get("title") or "").strip()
    if not title:
        raise AppError("Course title is required.", "VALIDATION_ERROR", 422)
    skills = data.get("skill_names") or []
    if isinstance(skills, str):
        skills = [item.strip() for item in skills.split(",") if item.strip()]
    modules = data.get("modules") or []
    if isinstance(modules, str):
        modules = [item.strip() for item in modules.replace("\r", "").split("\n") if item.strip()]
    payload = {
        "title": title[:160],
        "provider": (data.get("provider") or "")[:120],
        "description": (data.get("description") or "")[:2000],
        "url": (data.get("url") or "")[:400],
        "difficulty": (data.get("difficulty") or "BEGINNER").upper(),
        "duration_hours": data.get("duration_hours", 6),
        "skill_names": skills,
        "modules": modules,
        "is_active": bool(data.get("is_active", True)),
    }
    if payload["url"]:
        from app.utils.text import is_http_url

        if not is_http_url(payload["url"]):
            raise AppError("Course URL must start with http:// or https://.", "INVALID_URL", 422)
    return payload


@bp.get("/courses")
@api_roles_required(*ADMIN_ROLES)
def courses():
    return ok({"courses": courses_repo.list_courses(active_only=False)})


@bp.post("/courses")
@api_roles_required(*ADMIN_ROLES)
def create_course():
    course = courses_repo.create_course(_course_payload(json_body()))
    return ok(course, "Course created.", 201)


@bp.put("/courses/<course_id>")
@api_roles_required(*ADMIN_ROLES)
def update_course(course_id):
    existing = courses_repo.find_course(course_id)
    if not existing:
        raise AppError("Course not found.", "COURSE_NOT_FOUND", 404)
    payload = _course_payload(json_body())
    existing_module_ids = {module["title"]: module["id"] for module in existing.get("modules", [])}
    normalized_modules = []
    for item in payload.get("modules", []):
        title = item.get("title", "") if isinstance(item, dict) else str(item or "")
        title = title.strip()
        if title:
            normalized_modules.append({"title": title, "id": existing_module_ids.get(title, "")})
    payload["modules"] = normalized_modules
    course = courses_repo.update_course(course_id, payload)
    return ok(course, "Course updated.")


@bp.get("/learner/<user_id>")
@api_roles_required(*ADMIN_ROLES, "EMPLOYEE")
def learner_snapshot(user_id):
    actor = current_user()
    learner = users_repo.find_by_id(user_id)
    if not learner:
        raise AppError("Learner not found.", "NOT_FOUND", 404)
    if actor["role"] == ROLE_SUPER_ADMIN:
        pass
    elif actor["role"] in {ROLE_UNIVERSITY_ADMIN, ROLE_ORGANIZATION_ADMIN}:
        if learner.get("organization_id") != actor.get("organization_id"):
            raise AppError("You cannot access another organization's data.", "FORBIDDEN", 403)
    elif actor["role"] == "EMPLOYEE" and actor.get("is_expert"):
        assignments = operations_repo.list_assignments(actor["_id"])
        if not any(item.get("learner_id") == user_id for item in assignments):
            raise AppError("This learner is not assigned to you.", "FORBIDDEN", 403)
    else:
        raise AppError("You do not have permission to perform this action.", "FORBIDDEN", 403)
    return ok(analytics_service.learner_snapshot(learner))
