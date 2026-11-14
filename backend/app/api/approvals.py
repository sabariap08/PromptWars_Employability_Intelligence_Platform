"""Two-level approval endpoints for platform and organization administrators."""
from flask import Blueprint

from app.api.common import arg, json_body, pagination
from app.security.auth import (
    ROLE_ORGANIZATION_ADMIN,
    ROLE_SUPER_ADMIN,
    ROLE_UNIVERSITY_ADMIN,
    api_roles_required,
)
from app.services import approval_service
from app.utils.responses import ok

bp = Blueprint("approvals_api", __name__, url_prefix="/api/approvals")

ADMIN = (ROLE_UNIVERSITY_ADMIN, ROLE_ORGANIZATION_ADMIN)


@bp.get("/organizations")
@api_roles_required(ROLE_SUPER_ADMIN)
def organizations():
    page = pagination()
    items, total = approval_service.pending_organizations(
        status=arg("status", "PENDING_APPROVAL"),
        org_type=arg("type"),
        search=arg("q"),
        page=page["page"],
        page_size=page["page_size"],
    )
    return ok({"organizations": items, "total": total, "page": page["page"], "page_size": page["page_size"]})


@bp.post("/organizations/<org_id>/approve")
@api_roles_required(ROLE_SUPER_ADMIN)
def approve_organization(org_id):
    return ok(approval_service.approve_organization(org_id), "Organization approved.")


@bp.post("/organizations/<org_id>/reject")
@api_roles_required(ROLE_SUPER_ADMIN)
def reject_organization(org_id):
    org = approval_service.reject_organization(org_id, json_body().get("reason", ""))
    return ok(org, "Organization rejected.")


@bp.post("/organizations/<org_id>/status")
@api_roles_required(ROLE_SUPER_ADMIN)
def organization_status(org_id):
    data = json_body()
    org = approval_service.set_organization_status(
        org_id, (data.get("status") or "").upper(), data.get("reason", "")
    )
    return ok(org, "Organization status updated.")


@bp.get("/members")
@api_roles_required(*ADMIN)
def members():
    page = pagination()
    items, total = approval_service.pending_members(
        status=arg("status", "PENDING_APPROVAL"),
        search=arg("q"),
        page=page["page"],
        page_size=page["page_size"],
    )
    return ok({"members": items, "total": total, "page": page["page"], "page_size": page["page_size"]})


@bp.post("/members/<user_id>/approve")
@api_roles_required(*ADMIN)
def approve_member(user_id):
    return ok(approval_service.approve_member(user_id), "Member approved.")


@bp.post("/members/<user_id>/reject")
@api_roles_required(*ADMIN)
def reject_member(user_id):
    member = approval_service.reject_member(user_id, json_body().get("reason", ""))
    return ok(member, "Member rejected.")


@bp.post("/experts/<user_id>")
@api_roles_required(ROLE_ORGANIZATION_ADMIN)
def set_expert(user_id):
    data = json_body()
    member = approval_service.set_expert_capability(user_id, bool(data.get("enabled", True)))
    return ok(member, "Expert capability updated.")


@bp.post("/assignments")
@api_roles_required(*ADMIN)
def create_assignment():
    data = json_body()
    assignment = approval_service.assign_trainer(
        data.get("trainer_id", ""), data.get("learner_id", "")
    )
    return ok(assignment, "Trainer assigned to learner.", 201)
