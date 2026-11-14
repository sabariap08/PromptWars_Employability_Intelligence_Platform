"""Assessment endpoints for generation, attempts, submission and evaluation."""
from flask import Blueprint

from app.api.common import json_body
from app.orchestration.orchestrator import run_workflow
from app.repositories import assessments_repo, profiles_repo
from app.security.auth import LEARNER_ROLES, api_roles_required, current_user
from app.services import assessment_service
from app.utils.responses import AppError, ok

bp = Blueprint("assessments_api", __name__, url_prefix="/api/assessments")


@bp.get("")
@api_roles_required(*LEARNER_ROLES)
def list_assessments():
    return ok(assessment_service.list_assessments_for(current_user()))


@bp.post("/baseline")
@api_roles_required(*LEARNER_ROLES)
def create_baseline():
    assessment = assessment_service.create_baseline(current_user())
    return ok(assessment, "Baseline assessment prepared.", 201)


@bp.post("/skill-check")
@api_roles_required(*LEARNER_ROLES)
def create_skill_check():
    data = json_body()
    skills = data.get("skills") or []
    if isinstance(skills, str):
        skills = [item.strip() for item in skills.split(",") if item.strip()]
    assessment = assessment_service.create_skill_check(current_user(), skills, data.get("title"))
    return ok(assessment, "Skill check prepared.", 201)


@bp.post("/<assessment_id>/start")
@api_roles_required(*LEARNER_ROLES)
def start(assessment_id):
    attempt = assessment_service.start_attempt(current_user(), assessment_id)
    return ok(attempt, "Assessment started.", 201)


@bp.get("/attempts/<attempt_id>")
@api_roles_required(*LEARNER_ROLES)
def get_attempt(attempt_id):
    return ok(assessment_service.get_attempt(current_user(), attempt_id))


@bp.get("/attempts/<attempt_id>/result")
@api_roles_required(*LEARNER_ROLES)
def attempt_result(attempt_id):
    attempt = assessments_repo.find_attempt(attempt_id, current_user()["_id"])
    if not attempt:
        raise AppError("Assessment attempt not found.", "ATTEMPT_NOT_FOUND", 404)
    if attempt["status"] != "EVALUATED":
        raise AppError("This assessment has not been evaluated yet.", "NOT_EVALUATED", 409)
    return ok(assessment_service.result_view(attempt))


@bp.post("/attempts/<attempt_id>/submit")
@api_roles_required(*LEARNER_ROLES)
def submit(attempt_id):
    user = current_user()
    assessment_service.submit_answers(user, attempt_id, json_body())
    attempt = assessments_repo.find_attempt(attempt_id, user["_id"])
    workflow = run_workflow(
        "assessment.submitted",
        user,
        {"attempt_id": attempt_id, "assessment_title": attempt.get("title", "your assessment")},
    )
    evaluated = assessments_repo.find_attempt(attempt_id, user["_id"])
    if evaluated and evaluated["status"] == "SUBMITTED":
        evaluated = assessment_service.evaluate_attempt(attempt_id)
    return ok(
        {
            "attempt": assessment_service.result_view(evaluated),
            "workflow": workflow.get("executions", []),
        },
        "Assessment submitted and evaluated.",
    )


@bp.post("/certifications/<cert_id>/verify")
@api_roles_required(*LEARNER_ROLES)
def verify_certification(cert_id):
    user = current_user()
    cert = profiles_repo.find_certification(cert_id, user["_id"])
    if not cert:
        raise AppError("Certification not found.", "NOT_FOUND", 404)
    if cert.get("assessment_id"):
        return ok({"assessment_id": cert["assessment_id"]}, "Verification check already exists.")
    assessment = assessment_service.create_certification_check(user, cert)
    profiles_repo.update_certification(cert["_id"], {"assessment_id": assessment["_id"]})
    return ok({"assessment_id": assessment["_id"], "assessment": assessment}, "Verification check created.", 201)


@bp.post("/projects/<project_id>/follow-up")
@api_roles_required(*LEARNER_ROLES)
def project_follow_up(project_id):
    user = current_user()
    project = profiles_repo.find_project(project_id, user["_id"])
    if not project:
        raise AppError("Project not found.", "NOT_FOUND", 404)
    analysis = dict(project.get("ai_analysis") or {})
    if analysis.get("follow_up_assessment_id"):
        return ok({"assessment_id": analysis["follow_up_assessment_id"]}, "Follow-up already exists.")
    assessment = assessment_service.create_project_check(user, project)
    analysis["follow_up_assessment_id"] = assessment["_id"]
    profiles_repo.update_project(project["_id"], {"ai_analysis": analysis})
    return ok({"assessment_id": assessment["_id"], "assessment": assessment}, "Project follow-up created.", 201)
