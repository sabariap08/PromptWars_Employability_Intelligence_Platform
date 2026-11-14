"""Organization and membership approval workflows (two-level approvals)."""
from app.repositories import operations_repo, organizations_repo, users_repo
from app.security.auth import (
    ROLE_ORGANIZATION_ADMIN,
    ROLE_STUDENT,
    ROLE_SUPER_ADMIN,
    ROLE_UNIVERSITY_ADMIN,
    current_user,
    public_user,
)
from app.services import ops_service
from app.utils.ids import now_utc
from app.utils.responses import AppError
from app.utils.text import clean_text

ADMIN_ROLE_FOR_TYPE = {
    "UNIVERSITY": ROLE_UNIVERSITY_ADMIN,
    "COMPANY": ROLE_ORGANIZATION_ADMIN,
}


def _actor():
    actor = current_user()
    if not actor:
        raise AppError("Please sign in to continue.", "AUTH_REQUIRED", 401)
    return actor


def _admin_scope(actor: dict) -> str:
    if actor["role"] not in {ROLE_UNIVERSITY_ADMIN, ROLE_ORGANIZATION_ADMIN}:
        raise AppError("Only organization administrators can do this.", "FORBIDDEN", 403)
    if not actor.get("organization_id"):
        raise AppError("Your administrator account is not linked to an organization.", "NO_ORGANIZATION", 403)
    return actor["organization_id"]


def _join_applicant(org: dict) -> dict:
    applicant = users_repo.find_by_id((organizations_repo.find_request_by_org(org["_id"], "ORGANIZATION") or {}).get("applicant_user_id"))
    org = dict(org)
    org["applicant"] = public_user(applicant)
    return org


def pending_organizations(status: str = "PENDING_APPROVAL", org_type: str = "", search: str = "", page: int = 1, page_size: int = 20):
    actor = _actor()
    if actor["role"] != ROLE_SUPER_ADMIN:
        raise AppError("Only the platform owner can review organizations.", "FORBIDDEN", 403)
    items, total = organizations_repo.list_orgs(status, org_type, search, page, page_size)
    return [_join_applicant(item) for item in items], total


def approve_organization(org_id: str) -> dict:
    actor = _actor()
    if actor["role"] != ROLE_SUPER_ADMIN:
        raise AppError("Only the platform owner can approve organizations.", "FORBIDDEN", 403)
    org = organizations_repo.find_org(org_id)
    if not org:
        raise AppError("Organization not found.", "ORGANIZATION_NOT_FOUND", 404)
    if org.get("approval_status") != "PENDING_APPROVAL":
        raise AppError("This organization has already been reviewed.", "ALREADY_REVIEWED", 409)

    request_doc = organizations_repo.find_request_by_org(org_id, "ORGANIZATION")
    applicant = users_repo.find_by_id(request_doc.get("applicant_user_id")) if request_doc else None
    if not applicant or not applicant.get("email_verified"):
        raise AppError(
            "The administrator must verify their email before the organization can be approved.",
            "EMAIL_NOT_VERIFIED",
            422,
        )

    changed = organizations_repo.transition_org(
        org_id,
        "PENDING_APPROVAL",
        "APPROVED",
        approved_at=now_utc(),
        approved_by=actor["_id"],
        rejection_reason=None,
    )
    if not changed:
        raise AppError("This request was already processed by another administrator.", "CONFLICT", 409)

    users_repo.transition_status(
        applicant["_id"],
        "PENDING_APPROVAL",
        "APPROVED",
        approved_at=now_utc(),
        approved_by=actor["_id"],
        rejection_reason=None,
    )
    organizations_repo.resolve_request_for_org(org_id, "ORGANIZATION", "APPROVED", actor["_id"])
    ops_service.notify(
        applicant["_id"],
        org_id,
        "Organization approved",
        f"{org['name']} is now active on the Employability Intelligence Platform. You can sign in and start managing your members.",
        "SUCCESS",
        "/login",
    )
    ops_service.audit("ORGANIZATION_APPROVED", "organization", org_id, org["name"], org_id=org_id)
    return organizations_repo.find_org(org_id)


def reject_organization(org_id: str, reason: str) -> dict:
    actor = _actor()
    if actor["role"] != ROLE_SUPER_ADMIN:
        raise AppError("Only the platform owner can review organizations.", "FORBIDDEN", 403)
    reason = clean_text(reason, 500)
    if not reason:
        raise AppError("Please provide a reason for rejection.", "REASON_REQUIRED", 422)
    org = organizations_repo.find_org(org_id)
    if not org:
        raise AppError("Organization not found.", "ORGANIZATION_NOT_FOUND", 404)
    changed = organizations_repo.transition_org(
        org_id,
        "PENDING_APPROVAL",
        "REJECTED",
        rejection_reason=reason,
    )
    if not changed:
        raise AppError("This organization has already been reviewed.", "ALREADY_REVIEWED", 409)
    request_doc = organizations_repo.find_request_by_org(org_id, "ORGANIZATION")
    if request_doc:
        users_repo.transition_status(
            request_doc["applicant_user_id"],
            "PENDING_APPROVAL",
            "REJECTED",
            rejection_reason=reason,
        )
        ops_service.notify(
            request_doc["applicant_user_id"],
            org_id,
            "Registration not approved",
            f"Your organization registration was not approved. Reason: {reason}",
            "WARNING",
        )
    organizations_repo.resolve_request_for_org(org_id, "ORGANIZATION", "REJECTED", actor["_id"], reason)
    ops_service.audit("ORGANIZATION_REJECTED", "organization", org_id, reason, org_id=org_id)
    return organizations_repo.find_org(org_id)


def set_organization_status(org_id: str, new_status: str, reason: str = "") -> dict:
    actor = _actor()
    if actor["role"] != ROLE_SUPER_ADMIN:
        raise AppError("Only the platform owner can change organization status.", "FORBIDDEN", 403)
    if new_status not in {"SUSPENDED", "APPROVED", "INACTIVE"}:
        raise AppError("Unsupported status.", "INVALID_STATUS", 422)
    org = organizations_repo.find_org(org_id)
    if not org:
        raise AppError("Organization not found.", "ORGANIZATION_NOT_FOUND", 404)
    organizations_repo.update_org(
        org_id,
        {
            "approval_status": new_status,
            "rejection_reason": clean_text(reason, 500) if new_status != "APPROVED" else None,
        },
    )
    ops_service.audit(
        f"ORGANIZATION_{new_status}",
        "organization",
        org_id,
        clean_text(reason, 500),
        org_id=org_id,
    )
    return organizations_repo.find_org(org_id)


def pending_members(status: str = "PENDING_APPROVAL", search: str = "", page: int = 1, page_size: int = 20):
    actor = _actor()
    org_id = _admin_scope(actor)
    org = organizations_repo.find_org(org_id)
    if not org:
        raise AppError("Organization not found.", "ORGANIZATION_NOT_FOUND", 404)
    allowed_roles = [ROLE_STUDENT] if org["organization_type"] == "UNIVERSITY" else ["EMPLOYEE"]
    items, total = users_repo.list_by_org(
        org_id, roles=allowed_roles, statuses=[status], search=search, page=page, page_size=page_size
    )
    return [public_user(item) for item in items], total


def approve_member(user_id: str) -> dict:
    actor = _actor()
    org_id = _admin_scope(actor)
    org = organizations_repo.find_org(org_id)
    if not org or org.get("approval_status") != "APPROVED":
        raise AppError("Your organization must be active to approve members.", "ORGANIZATION_INACTIVE", 403)
    member = users_repo.find_by_id(user_id)
    if not member or member.get("organization_id") != org_id:
        raise AppError("This registration does not belong to your organization.", "FORBIDDEN", 403)
    expected_role = ROLE_STUDENT if org["organization_type"] == "UNIVERSITY" else "EMPLOYEE"
    if member.get("role") != expected_role:
        raise AppError("This account type cannot be approved here.", "INVALID_ROLE", 422)
    if not member.get("email_verified"):
        raise AppError("The member must verify their email first.", "EMAIL_NOT_VERIFIED", 422)
    if member.get("account_status") != "PENDING_APPROVAL":
        raise AppError("This registration has already been reviewed.", "ALREADY_REVIEWED", 409)

    changed = users_repo.transition_status(
        user_id,
        "PENDING_APPROVAL",
        "APPROVED",
        approved_at=now_utc(),
        approved_by=actor["_id"],
        rejection_reason=None,
    )
    if not changed:
        raise AppError("This request was already processed by another administrator.", "CONFLICT", 409)

    organizations_repo.resolve_request_for_user(user_id, "MEMBERSHIP", "APPROVED", actor["_id"])
    ops_service.notify(
        user_id,
        org_id,
        "Your account is approved",
        "Your membership has been approved. Sign in to complete your profile and start your first assessment.",
        "SUCCESS",
        "/login",
    )
    ops_service.audit("MEMBERSHIP_APPROVED", "user", user_id, member.get("email", ""), org_id=org_id)
    return public_user(users_repo.find_by_id(user_id))


def reject_member(user_id: str, reason: str) -> dict:
    actor = _actor()
    org_id = _admin_scope(actor)
    reason = clean_text(reason, 500)
    if not reason:
        raise AppError("Please provide a reason for rejection.", "REASON_REQUIRED", 422)
    member = users_repo.find_by_id(user_id)
    if not member or member.get("organization_id") != org_id:
        raise AppError("This registration does not belong to your organization.", "FORBIDDEN", 403)
    if member.get("account_status") != "PENDING_APPROVAL":
        raise AppError("This registration has already been reviewed.", "ALREADY_REVIEWED", 409)
    users_repo.transition_status(
        user_id,
        "PENDING_APPROVAL",
        "REJECTED",
        rejection_reason=reason,
    )
    organizations_repo.resolve_request_for_user(user_id, "MEMBERSHIP", "REJECTED", actor["_id"], reason)
    ops_service.notify(
        user_id,
        org_id,
        "Registration not approved",
        f"Your registration was not approved. Reason: {reason}",
        "WARNING",
    )
    ops_service.audit("MEMBERSHIP_REJECTED", "user", user_id, reason, org_id=org_id)
    return public_user(users_repo.find_by_id(user_id))


def set_expert_capability(user_id: str, enabled: bool) -> dict:
    actor = _actor()
    org_id = _admin_scope(actor)
    org = organizations_repo.find_org(org_id)
    if not org or org.get("organization_type") != "COMPANY":
        raise AppError("Expert capabilities are available for organizations only.", "FORBIDDEN", 403)
    member = users_repo.find_by_id(user_id)
    if not member or member.get("organization_id") != org_id or member.get("role") != "EMPLOYEE":
        raise AppError("Employee not found in your organization.", "NOT_FOUND", 404)
    users_repo.update_user(user_id, {"is_expert": bool(enabled)})
    ops_service.audit(
        "EXPERT_CAPABILITY_CHANGED",
        "user",
        user_id,
        "enabled" if enabled else "disabled",
        org_id=org_id,
    )
    return public_user(users_repo.find_by_id(user_id))


def list_learners(status: str = "APPROVED", search: str = "", page: int = 1, page_size: int = 20):
    actor = _actor()
    org_id = _admin_scope(actor)
    org = organizations_repo.find_org(org_id)
    roles = [ROLE_STUDENT] if org["organization_type"] == "UNIVERSITY" else ["EMPLOYEE"]
    items, total = users_repo.list_by_org(
        org_id, roles=roles, statuses=[status] if status else None, search=search, page=page, page_size=page_size
    )
    departments = {d["_id"]: d["name"] for d in organizations_repo.list_departments(org_id)}
    result = []
    for item in items:
        user = public_user(item)
        user["department_name"] = departments.get(item.get("department_id"), "")
        result.append(user)
    return result, total


def assign_trainer(trainer_id: str, learner_id: str) -> dict:
    actor = _actor()
    org_id = _admin_scope(actor)
    trainer = users_repo.find_by_id(trainer_id)
    learner = users_repo.find_by_id(learner_id)
    if not trainer or trainer.get("organization_id") != org_id:
        raise AppError("Trainer not found in your organization.", "NOT_FOUND", 404)
    if not learner or learner.get("organization_id") != org_id:
        raise AppError("Learner not found in your organization.", "NOT_FOUND", 404)
    if not trainer.get("is_expert"):
        raise AppError("Enable expert capability for the trainer first.", "EXPERT_REQUIRED", 422)
    assignment = operations_repo.create_assignment(trainer_id, learner_id, org_id, actor["_id"])
    ops_service.notify(
        trainer_id,
        org_id,
        "New learner assigned",
        f"{learner.get('full_name')} has been assigned to you for review.",
        "INFO",
        "/app/expert",
    )
    ops_service.audit("TRAINER_ASSIGNED", "user", learner_id, trainer_id, org_id=org_id)
    return assignment
