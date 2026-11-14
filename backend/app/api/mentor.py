"""AI mentor endpoints."""
from flask import Blueprint

from app.api.common import json_body
from app.security.auth import LEARNER_ROLES, api_roles_required, current_user
from app.security.rate_limit import limiter
from app.services import context_service, mentor_service
from app.utils.responses import ok

bp = Blueprint("mentor_api", __name__, url_prefix="/api/mentor")


@bp.get("/history")
@api_roles_required(*LEARNER_ROLES)
def history():
    user = current_user()
    context = context_service.build(user)
    return ok(
        {
            "messages": mentor_service.history(user),
            "suggestions": mentor_service.suggestions(context),
            "context": context,
        }
    )


@bp.post("/chat")
@api_roles_required(*LEARNER_ROLES)
@limiter.limit("30 per minute")
def chat():
    result = mentor_service.chat(current_user(), json_body().get("message", ""))
    return ok(result, "Mentor replied.")


@bp.get("/context")
@api_roles_required(*LEARNER_ROLES)
def context():
    return ok(context_service.build(current_user()))
