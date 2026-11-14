"""Learning roadmap endpoints."""
from flask import Blueprint

from app.api.common import arg, json_body
from app.repositories import catalog_repo, learning_repo
from app.security.auth import LEARNER_ROLES, api_roles_required, current_user
from app.services import course_service, learning_service
from app.utils.responses import AppError, ok

bp = Blueprint("learning_api", __name__, url_prefix="/api/learning")


@bp.get("/roadmap")
@api_roles_required(*LEARNER_ROLES)
def roadmap():
    user = current_user()
    active = learning_repo.active_roadmap(user["_id"])
    return ok(
        {
            "roadmap": active,
            "summary": learning_service.roadmap_summary(active),
            "versions": [
                {
                    "_id": item["_id"],
                    "version": item.get("version", 1),
                    "status": item.get("status"),
                    "trigger": item.get("trigger"),
                    "career_name": item.get("career_name"),
                    "created_at": item.get("created_at"),
                }
                for item in learning_repo.list_roadmaps(user["_id"])
            ],
        }
    )


@bp.post("/roadmap/generate")
@api_roles_required(*LEARNER_ROLES)
def generate():
    roadmap = learning_service.generate_roadmap(current_user(), trigger="manual")
    return ok(
        {"roadmap": roadmap, "summary": learning_service.roadmap_summary(roadmap)},
        "Learning plan generated.",
        201,
    )


@bp.post("/tasks/<task_id>")
@api_roles_required(*LEARNER_ROLES)
def update_task(task_id):
    data = json_body()
    roadmap = learning_service.update_task(
        current_user(), task_id, data.get("action", ""), data.get("evidence_url", "")
    )
    return ok(
        {"summary": learning_service.roadmap_summary(roadmap), "roadmap": roadmap},
        "Learning task updated.",
    )


@bp.get("/activity")
@api_roles_required(*LEARNER_ROLES)
def activity():
    try:
        limit = max(1, min(100, int(arg("limit", "30") or 30)))
    except ValueError:
        limit = 30
    return ok({"activity": learning_repo.list_activity(current_user()["_id"], limit=limit)})


@bp.get("/resources")
@api_roles_required(*LEARNER_ROLES)
def resources():
    skill_name = arg("skill") or None
    return ok({"resources": catalog_repo.list_resources(skill_name, limit=100)})


@bp.get("/courses")
@api_roles_required(*LEARNER_ROLES)
def courses():
    items = course_service.list_courses(
        current_user(),
        search=arg("q"),
        skill=arg("skill"),
        difficulty=arg("difficulty"),
    )
    return ok({"courses": items, "total": len(items)})


@bp.get("/courses/<course_id>")
@api_roles_required(*LEARNER_ROLES)
def course_detail(course_id):
    return ok({"course": course_service.get_course(current_user(), course_id)})


@bp.post("/courses/<course_id>/enroll")
@api_roles_required(*LEARNER_ROLES)
def enroll_course(course_id):
    result = course_service.enroll(current_user(), course_id)
    message = "Already enrolled in this course." if result["already_enrolled"] else "Enrolled successfully."
    return ok(result, message, 200 if result["already_enrolled"] else 201)


@bp.get("/enrollments")
@api_roles_required(*LEARNER_ROLES)
def enrollments():
    return ok({"courses": course_service.my_enrollments(current_user())})


@bp.post("/enrollments/<enrollment_id>/progress")
@api_roles_required(*LEARNER_ROLES)
def update_enrollment_progress(enrollment_id):
    data = json_body()
    module_id = (data.get("module_id") or "").strip()
    if not module_id:
        raise AppError("A module is required.", "VALIDATION_ERROR", 422)
    course = course_service.update_progress(
        current_user(), enrollment_id, module_id, bool(data.get("completed", True))
    )
    return ok({"course": course}, "Course progress updated.")


@bp.get("/recommended-courses")
@api_roles_required(*LEARNER_ROLES)
def recommended_courses():
    try:
        limit = max(1, min(20, int(arg("limit", "6") or 6)))
    except ValueError:
        limit = 6
    return ok({"courses": course_service.recommended_courses(current_user(), limit=limit)})


@bp.get("/leaderboard")
@api_roles_required(*LEARNER_ROLES)
def leaderboard():
    try:
        limit = max(1, min(50, int(arg("limit", "20") or 20)))
    except ValueError:
        limit = 20
    scope = "platform" if arg("scope") == "platform" else "organization"
    return ok(course_service.leaderboard(current_user(), scope=scope, limit=limit))
