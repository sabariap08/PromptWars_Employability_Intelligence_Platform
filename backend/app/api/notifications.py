"""Notifications available to every signed-in account."""
from flask import Blueprint

from app.api.common import json_body, pagination
from app.repositories import operations_repo
from app.security.auth import api_login_required, current_user
from app.utils.responses import ok

bp = Blueprint("notifications_api", __name__, url_prefix="/api/notifications")


@bp.get("")
@api_login_required
def notifications():
    user = current_user()
    page = pagination()
    return ok(
        {
            "notifications": operations_repo.list_notifications(user["_id"], limit=page["page_size"]),
            "unread": operations_repo.unread_count(user["_id"]),
        }
    )


@bp.post("/read")
@api_login_required
def mark_read():
    user = current_user()
    operations_repo.mark_read(user["_id"], json_body().get("id"))
    return ok({"unread": operations_repo.unread_count(user["_id"])}, "Notifications updated.")
