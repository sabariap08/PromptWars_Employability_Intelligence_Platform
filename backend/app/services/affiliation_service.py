"""Learner-initiated organization change requests with administrator review."""
from app.repositories import (
    affiliations_repo,
    organizations_repo,
    profiles_repo,
    users_repo,
)
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

ADMIN_FOR_TYPE = {
    "UNIVERSITY": ROLE_UNIVERSITY_ADMIN,
    "COMPANY": ROLE_ORGANIZATION_ADMIN,
}


def _actor() -> dict:
    actor = current_user()
    if not actor:
        raise AppError("Please sign in to continue.", "AUTH_REQUIRED", 401)
    return actor


def _learner_org_type(role: str) -> str:
    return "UNIVERSITY" if role == ROLE_STUDENT else "COMPANY"


def _enrich(request: dict) -> dict:
    item = dict(request)
    user = users_repo.find_by_id(request.get("user_id"))
    current_org = organizations_repo.find_org(request.get("current_organization_id"))
    requested_org = organizations_repo.find_org(request.get("requested_organization_id"))
    department = organizations_repo.find_department(request.get("requested_department_id"))
    item["user"] = public_user(user)
    item["current_organization"] = {"_id": current_org["_id"], "name": current_org["name"]} if current_org else None
    item["requested_organization"] = (
        {"_id": requested_org["_id"], "name": requested_org["name"]} if requested_org else None
    )
    item["requested_department"] = (
        {"_id": department["_id"], "name": department["name"]} if department else None
    )
    return item


def create_request(payload: dict) -> dict:
    user = _actor()
    if user.get("role") not in {ROLE_STUDENT, "EMPLOYEE"}:
        raise AppError("Only learners can request an affiliation change.", "FORBIDDEN", 403)
    requested_org_id = clean_text(payload.get("organization_id"), 80)
    department_id = clean_text(payload.get("department_id"), 80)
    reason = clean_text(payload.get("reason"), 1000)
    if not requested_org_id or not reason:
        raise AppError("Choose an organization and explain the reason.", "VALIDATION_ERROR", 422)
    if requested_org_id == user.get("organization_id"):
        raise AppError("Choose a different organization.", "SAME_ORGANIZATION", 422)
    if affiliations_repo.find_pending_for_user(user["_id"]):
        raise AppError("You already have a pending affiliation request.", "REQUEST_PENDING", 409)

    org = organizations_repo.find_org(requested_org_id)
    expected_type = _learner_org_type(user.get("role"))
    if not org or org.get("organization_type") != expected_type or org.get("approval_status") != "APPROVED":
        raise AppError("Choose an active organization of the correct type.", "INVALID_ORGANIZATION", 422)
    department = None
    if department_id:
        department = organizations_repo.find_department(department_id)
        if not department or department.get("organization_id") != org["_id"]:
            raise AppError("Choose a valid department in the selected organization.", "INVALID_DEPARTMENT", 422)

    request = affiliations_repo.create_request(
        {
            "user_id": user["_id"],
            "current_organization_id": user.get("organization_id"),
            "requested_organization_id": org["_id"],
            "requested_department_id": department["_id"] if department else None,
            "reason": reason,
        }
    )
    current_admin_role = ADMIN_FOR_TYPE.get(expected_type)
    current_admins, _ = users_repo.list_by_org(
        user.get("organization_id"),
        roles=[current_admin_role],
        statuses=["APPROVED"],
        page_size=50,
    )
    target_admins, _ = users_repo.list_by_org(
        org["_id"], roles=[current_admin_role], statuses=["APPROVED"], page_size=50
    )
    ops_service.notify_many(
        [admin["_id"] for admin in current_admins + target_admins],
        user.get("organization_id"),
        "Affiliation change requested",
        f"{user.get('full_name')} requested a move to {org['name']}.",
        "APPROVAL",
        "/app/requests",
    )
    ops_service.audit(
        "AFFILIATION_REQUESTED",
        "affiliation_request",
        request["_id"],
        f"{user.get('organization_id')} -> {org['_id']}",
        org_id=user.get("organization_id"),
    )
    return _enrich(request)


def list_my_requests() -> list:
    user = _actor()
    return [_enrich(item) for item in affiliations_repo.list_for_user(user["_id"])]


def list_requests(status: str = "", search: str = "", limit: int = 100) -> list:
    actor = _actor()
    if actor["role"] == ROLE_SUPER_ADMIN:
        org_id = None
    elif actor["role"] in {ROLE_UNIVERSITY_ADMIN, ROLE_ORGANIZATION_ADMIN}:
        org_id = actor.get("organization_id")
    else:
        raise AppError("Only administrators can review affiliation requests.", "FORBIDDEN", 403)
    items = affiliations_repo.list_for_organization(org_id, status, search, limit)
    if org_id:
        items = [
            item
            for item in items
            if org_id in {item.get("current_organization_id"), item.get("requested_organization_id")}
        ]
    return [_enrich(item) for item in items]


def review_request(request_id: str, decision: str, note: str = "") -> dict:
    actor = _actor()
    request = affiliations_repo.find_request(request_id)
    if not request:
        raise AppError("Affiliation request not found.", "NOT_FOUND", 404)
    if request.get("status") != "PENDING":
        raise AppError("This request has already been reviewed.", "ALREADY_REVIEWED", 409)
    if actor["role"] == ROLE_SUPER_ADMIN:
        pass
    elif actor["role"] in {ROLE_UNIVERSITY_ADMIN, ROLE_ORGANIZATION_ADMIN}:
        if actor.get("organization_id") not in {
            request.get("current_organization_id"),
            request.get("requested_organization_id"),
        }:
            raise AppError("This request belongs to another organization.", "FORBIDDEN", 403)
    else:
        raise AppError("Only administrators can review affiliation requests.", "FORBIDDEN", 403)

    decision = (decision or "").upper()
    if decision not in {"APPROVED", "REJECTED"}:
        raise AppError("Decision must be approved or rejected.", "INVALID_DECISION", 422)
    note = clean_text(note, 500)
    if decision == "REJECTED" and not note:
        raise AppError("Provide a reason for rejecting the request.", "REASON_REQUIRED", 422)

    if decision == "APPROVED":
        user = users_repo.find_by_id(request["user_id"])
        if not user:
            raise AppError("The learner account no longer exists.", "NOT_FOUND", 404)
        users_repo.update_user(
            user["_id"],
            {
                "organization_id": request["requested_organization_id"],
                "department_id": request.get("requested_department_id"),
                "affiliation_updated_at": now_utc(),
            },
        )
        profiles_repo.update_profile(
            user["_id"],
            {
                "organization_id": request["requested_organization_id"],
                "affiliation_updated_at": now_utc(),
            },
        )

    if not affiliations_repo.resolve(request_id, decision, actor["_id"], note):
        raise AppError("This request was already processed.", "CONFLICT", 409)
    org = organizations_repo.find_org(request.get("requested_organization_id"))
    title = "Affiliation request approved" if decision == "APPROVED" else "Affiliation request declined"
    message = (
        f"Your move to {org['name']} was approved."
        if decision == "APPROVED" and org
        else f"Your affiliation change was declined. Reason: {note}"
    )
    ops_service.notify(
        request["user_id"],
        request.get("requested_organization_id"),
        title,
        message,
        "SUCCESS" if decision == "APPROVED" else "WARNING",
        "/app/profile",
    )
    ops_service.audit(
        f"AFFILIATION_{decision}",
        "affiliation_request",
        request_id,
        note,
        org_id=actor.get("organization_id"),
    )
    return _enrich(affiliations_repo.find_request(request_id))
