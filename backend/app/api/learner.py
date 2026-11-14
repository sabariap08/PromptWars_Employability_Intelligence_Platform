"""Learner endpoints: profile, evidence, career goals, notifications and expert review."""
from flask import Blueprint, request

from app.api.common import arg, json_body, pagination
from app.orchestration.orchestrator import run_workflow
from app.repositories import (
    learning_repo,
    operations_repo,
    organizations_repo,
    profiles_repo,
    users_repo,
)
from app.security.auth import LEARNER_ROLES, api_roles_required, current_user
from app.services import (
    affiliation_service,
    analytics_service,
    career_service,
    learning_service,
    profile_service,
    progress_service,
    skill_service,
)
from app.utils.responses import AppError, ok

bp = Blueprint("learner_api", __name__, url_prefix="/api/learner")


def _user():
    return current_user()


def _require_expert() -> dict:
    user = _user()
    if not user.get("is_expert"):
        raise AppError("Expert capability is required for this action.", "FORBIDDEN", 403)
    return user


def _assigned_learner(trainer: dict, learner_id: str) -> dict:
    """Cross-organization mentoring is allowed when an explicit assignment exists."""
    assignments = operations_repo.list_assignments(trainer["_id"])
    if not any(item.get("learner_id") == learner_id for item in assignments):
        raise AppError("This learner is not assigned to you.", "FORBIDDEN", 403)
    learner = users_repo.find_by_id(learner_id)
    if not learner:
        raise AppError("Learner not found.", "NOT_FOUND", 404)
    return learner


@bp.get("/profile")
@api_roles_required(*LEARNER_ROLES)
def get_profile():
    return ok(profile_service.get_bundle(_user()))


@bp.route("/profile", methods=["POST", "PUT"])
@api_roles_required(*LEARNER_ROLES)
def save_profile():
    user = _user()
    before = profiles_repo.find_profile(user["_id"]) or {}
    profile = profile_service.save_profile(user, json_body())
    workflow = []
    if profile.get("onboarding_complete") and not before.get("onboarding_complete"):
        workflow = run_workflow("profile.completed", user, {}).get("executions", [])
    return ok({"profile": profile, "workflow": workflow}, "Profile saved.")


@bp.get("/affiliation-requests")
@api_roles_required(*LEARNER_ROLES)
def affiliation_requests():
    return ok({"requests": affiliation_service.list_my_requests()})

@bp.post("/affiliation-request")
@api_roles_required(*LEARNER_ROLES)
def create_affiliation_request():
    return ok(affiliation_service.create_request(json_body()), "Affiliation request submitted.", 201)

@bp.get("/affiliation-options")
@api_roles_required(*LEARNER_ROLES)
def affiliation_options():
    user = _user()
    org_type = "UNIVERSITY" if user.get("role") == "STUDENT" else "COMPANY"
    orgs = []
    for org in organizations_repo.search_approved("", org_type, limit=100):
        if org["_id"] == user.get("organization_id"):
            continue
        item = dict(org)
        item["departments"] = organizations_repo.list_departments(org["_id"])
        orgs.append(item)
    return ok({"organizations": orgs})

@bp.post("/skills")
@api_roles_required(*LEARNER_ROLES)
def add_skill():
    user = _user()
    data = json_body()
    name = (data.get("name") or "").strip()
    if not name:
        raise AppError("Skill name is required.", "VALIDATION_ERROR", 422, {"field": "name"})
    skill = skill_service.add_self_skill(
        user["_id"], user.get("organization_id"), name[:80], (data.get("level") or "BEGINNER").upper()
    )
    return ok(skill, "Skill updated.", 201)


@bp.delete("/skills/<path:skill_name>")
@api_roles_required(*LEARNER_ROLES)
def remove_skill(skill_name):
    user = _user()
    skill_service.remove_self_skill(user["_id"], skill_name)
    return ok({"skill_name": skill_name}, "Skill removed.")


@bp.get("/certifications")
@api_roles_required(*LEARNER_ROLES)
def certifications():
    return ok({"certifications": profiles_repo.list_certifications(_user()["_id"])})


@bp.post("/certifications")
@api_roles_required(*LEARNER_ROLES)
def add_certification():
    user = _user()
    skills = request.form.getlist("skills")
    if len(skills) == 1 and "," in skills[0]:
        skills = [item.strip() for item in skills[0].split(",") if item.strip()]
    payload = {
        "name": request.form.get("name", ""),
        "issuer": request.form.get("issuer", ""),
        "issued_on": request.form.get("issued_on", ""),
        "skills": skills,
    }
    cert = profile_service.add_certification(user, payload, request.files.get("file"))
    workflow = run_workflow("certification.added", user, {"certification_id": cert["_id"]})
    assessment_id = (workflow.get("results", {}).get("assessment") or {}).get("assessment_id")
    return ok(
        {"certification": cert, "assessment_id": assessment_id, "workflow": workflow.get("executions", [])},
        "Certification submitted for verification.",
        201,
    )


@bp.get("/projects")
@api_roles_required(*LEARNER_ROLES)
def projects():
    return ok({"projects": profiles_repo.list_projects(_user()["_id"])})


@bp.post("/projects")
@api_roles_required(*LEARNER_ROLES)
def add_project():
    user = _user()
    project = profile_service.add_project(user, json_body())
    workflow = run_workflow("project.added", user, {"project_id": project["_id"]})
    assessment_id = (workflow.get("results", {}).get("assessment") or {}).get("assessment_id")
    return ok(
        {"project": project, "assessment_id": assessment_id, "workflow": workflow.get("executions", [])},
        "Project submitted.",
        201,
    )


@bp.post("/career")
@api_roles_required(*LEARNER_ROLES)
def set_career():
    user = _user()
    data = json_body()
    role = career_service.set_target_career(user["_id"], data.get("career_id", ""))
    workflow = run_workflow("career.changed", user, {"career_id": role["_id"]})
    return ok(
        {
            "career": {"_id": role["_id"], "name": role["name"]},
            "readiness": career_service.readiness_summary(user["_id"]),
            "workflow": workflow.get("executions", []),
        },
        f"Career goal set to {role['name']}.",
    )


@bp.get("/readiness")
@api_roles_required(*LEARNER_ROLES)
def readiness():
    return ok(career_service.readiness_summary(_user()["_id"]))


@bp.get("/dashboard")
@api_roles_required(*LEARNER_ROLES)
def dashboard():
    return ok(progress_service.dashboard(_user()))


@bp.get("/progress")
@api_roles_required(*LEARNER_ROLES)
def progress():
    return ok(progress_service.compute(_user()))


@bp.get("/activity")
@api_roles_required(*LEARNER_ROLES)
def activity():
    try:
        limit = max(1, min(100, int(arg("limit", "30") or 30)))
    except ValueError:
        limit = 30
    return ok({"activity": learning_repo.list_activity(_user()["_id"], limit=limit)})


@bp.get("/notifications")
@api_roles_required(*LEARNER_ROLES)
def notifications():
    user = _user()
    page = pagination()
    return ok(
        {
            "notifications": operations_repo.list_notifications(user["_id"], limit=page["page_size"]),
            "unread": operations_repo.unread_count(user["_id"]),
        }
    )


@bp.post("/notifications/read")
@api_roles_required(*LEARNER_ROLES)
def mark_notifications_read():
    user = _user()
    notification_id = json_body().get("id")
    operations_repo.mark_read(user["_id"], notification_id)
    return ok({"unread": operations_repo.unread_count(user["_id"])}, "Notifications updated.")


@bp.get("/expert/learners")
@api_roles_required(*LEARNER_ROLES)
def expert_learners():
    trainer = _require_expert()
    results = []
    for assignment in operations_repo.list_assignments(trainer["_id"]):
        learner = users_repo.find_by_id(assignment.get("learner_id"))
        if not learner:
            continue
        analysis = career_service.analyze(learner["_id"]) or {}
        results.append(
            {
                "_id": learner["_id"],
                "full_name": learner.get("full_name"),
                "email": learner.get("email"),
                "department_id": learner.get("department_id"),
                "career_name": analysis.get("career_name", ""),
                "readiness": analysis.get("readiness", 0),
                "assigned_at": assignment.get("created_at"),
            }
        )
    return ok({"learners": results})


@bp.get("/expert/learners/<learner_id>")
@api_roles_required(*LEARNER_ROLES)
def expert_learner_detail(learner_id):
    trainer = _require_expert()
    learner = _assigned_learner(trainer, learner_id)
    snapshot = analytics_service.learner_snapshot(learner)
    snapshot["feedback"] = operations_repo.list_feedback(learner_id)
    return ok(snapshot)


@bp.post("/expert/feedback")
@api_roles_required(*LEARNER_ROLES)
def expert_feedback():
    trainer = _require_expert()
    data = json_body()
    learner_id = data.get("learner_id", "")
    learner = _assigned_learner(trainer, learner_id)
    skill_name = (data.get("skill_name") or "").strip()
    if not skill_name:
        raise AppError("Skill is required.", "VALIDATION_ERROR", 422, {"field": "skill_name"})
    try:
        rating = max(1, min(5, int(data.get("rating", 3))))
    except (TypeError, ValueError):
        rating = 3
    feedback = operations_repo.create_feedback(
        {
            "trainer_id": trainer["_id"],
            "learner_id": learner["_id"],
            "organization_id": trainer.get("organization_id"),
            "skill_name": skill_name,
            "rating": rating,
            "feedback": (data.get("feedback") or "")[:2000],
        }
    )
    skill_service.add_evidence(
        learner["_id"],
        learner.get("organization_id"),
        skill_name,
        "TRAINER",
        rating * 20,
        title="Trainer review",
        source_id=feedback["_id"],
        verified=rating >= 3,
    )
    if data.get("task_id"):
        learning_service.mark_task_verified(learner, data["task_id"])
    workflow = run_workflow("trainer.feedback", learner, {"skill_name": skill_name, "rating": rating})
    return ok(
        {"feedback": feedback, "workflow": workflow.get("executions", [])},
        "Feedback recorded and added as evidence.",
        201,
    )
