"""Public catalog and approved-organization search endpoints."""
from flask import Blueprint

from app.api.common import arg
from app.repositories import catalog_repo, organizations_repo
from app.utils.responses import ok

bp = Blueprint("public_api", __name__, url_prefix="/api/public")


@bp.get("/health")
def health():
    from flask import current_app
    from app.database.mongo import db_mode

    return ok({"status": "ok", "database_mode": db_mode(), "app": current_app.config["APP_NAME"]})


@bp.get("/organizations")
def organizations():
    org_type = (arg("type", "UNIVERSITY") or "UNIVERSITY").upper()
    if org_type not in {"UNIVERSITY", "COMPANY"}:
        org_type = "UNIVERSITY"
    query = arg("q")
    try:
        limit = max(1, min(25, int(arg("limit", "12") or 12)))
    except ValueError:
        limit = 12
    items = organizations_repo.search_approved(query, org_type, limit=limit)
    results = []
    for org in items:
        results.append(
            {
                "_id": org["_id"],
                "name": org.get("name", ""),
                "organization_type": org.get("organization_type"),
                "subtype": org.get("subtype", ""),
                "industry": org.get("industry", ""),
                "city": (org.get("location") or {}).get("city", ""),
                "state": (org.get("location") or {}).get("state", ""),
                "country": (org.get("location") or {}).get("country", ""),
                "website": org.get("website", ""),
                "departments": [
                    {"_id": dept["_id"], "name": dept.get("name", ""), "code": dept.get("code", "")}
                    for dept in organizations_repo.list_departments(org["_id"])
                ],
            }
        )
    return ok({"organizations": results, "count": len(results)})


@bp.get("/careers")
def careers():
    items = []
    for role in catalog_repo.list_careers():
        items.append(
            {
                "_id": role["_id"],
                "name": role["name"],
                "description": role.get("description", ""),
                "experience_level": role.get("experience_level", ""),
                "required_skills": [item.get("skill_name") for item in role.get("required_skills", [])],
                "preferred_skills": [item.get("skill_name") for item in role.get("preferred_skills", [])],
                "project_expectations": role.get("project_expectations", ""),
            }
        )
    return ok({"careers": items, "count": len(items)})


@bp.get("/skills")
def skills():
    return ok({"skills": catalog_repo.list_skills()})


@bp.get("/resources")
def resources():
    skill_name = arg("skill") or None
    return ok({"resources": catalog_repo.list_resources(skill_name, limit=200)})
