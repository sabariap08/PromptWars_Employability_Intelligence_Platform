"""Learning roadmap endpoints."""
from flask import Blueprint

from app.api.common import arg, json_body
from app.repositories import catalog_repo, learning_repo
from app.security.auth import LEARNER_ROLES, api_roles_required, current_user
from app.services import learning_service
from app.utils.responses import ok

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
