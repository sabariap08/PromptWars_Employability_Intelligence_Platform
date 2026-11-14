"""Organization-admin context and analytics endpoints."""
from flask import Blueprint

from app.api.common import arg, json_body, pagination
from app.repositories import operations_repo, organizations_repo, users_repo
from app.security.auth import (
    ROLE_ORGANIZATION_ADMIN,
    ROLE_UNIVERSITY_ADMIN,
    api_roles_required,
    current_user,
)
from app.services import analytics_service, approval_service, ops_service
from app.utils.responses import AppError, ok

bp = Blueprint("organizations_api", __name__, url_prefix="/api/organizations")

ORG_ADMIN = (ROLE_UNIVERSITY_ADMIN, ROLE_ORGANIZATION_ADMIN)


def _admin_context():
    user = current_user()
    if not user.get("organization_id"):
        raise AppError("Your administrator account is not linked to an organization.", "NO_ORGANIZATION", 403)
    org = organizations_repo.find_org(user["organization_id"])
    if not org:
        raise AppError("Organization not found.", "ORGANIZATION_NOT_FOUND", 404)
    return user, org


@bp.get("/me")
@api_roles_required(*ORG_ADMIN)
def my_organization():
    user, org = _admin_context()
    departments = organizations_repo.list_departments(org["_id"])
    return ok({"organization": org, "departments": departments, "admin": user})


@bp.get("/me/overview")
@api_roles_required(*ORG_ADMIN)
def overview():
    _, org = _admin_context()
    return ok(analytics_service.org_overview(org["_id"], org["organization_type"]))


@bp.get("/me/learners")
@api_roles_required(*ORG_ADMIN)
def learners():
    page = pagination()
    items, total = approval_service.list_learners(
        status=arg("status", "APPROVED"),
        search=arg("q"),
        page=page["page"],
        page_size=page["page_size"],
    )
    return ok({"learners": items, "total": total, "page": page["page"], "page_size": page["page_size"]})


@bp.get("/me/trainers")
@api_roles_required(*ORG_ADMIN)
def trainers():
    _, org = _admin_context()
    items, _ = users_repo.list_by_org(
        org["_id"], roles=["EMPLOYEE"], statuses=["APPROVED"], page=1, page_size=1000
    )
    return ok({"trainers": [item for item in items if item.get("is_expert")]})


@bp.post("/me/departments")
@api_roles_required(*ORG_ADMIN)
def create_department():
    _, org = _admin_context()
    data = json_body()
    name = (data.get("name") or "").strip()
    if not name:
        raise AppError("Department name is required.", "VALIDATION_ERROR", 422)
    department = organizations_repo.create_department(org["_id"], name[:120], (data.get("code") or "")[:20])
    ops_service.audit("DEPARTMENT_CREATED", "department", department["_id"], name, org_id=org["_id"])
    return ok(department, "Department created.", 201)


@bp.get("/me/audit")
@api_roles_required(*ORG_ADMIN)
def audit_log():
    _, org = _admin_context()
    try:
        limit = max(1, min(200, int(arg("limit", "100") or 100)))
    except ValueError:
        limit = 100
    return ok({"logs": operations_repo.list_audit(limit=limit, org_id=org["_id"])})
