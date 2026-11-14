"""Notifications, audit logging and safe logging helpers."""
import logging

from app.repositories import operations_repo
from app.security.auth import current_user

logger = logging.getLogger("eip")


def notify(user_id: str, org_id: str | None, title: str, message: str, kind: str = "INFO", link: str = "") -> dict:
    return operations_repo.create_notification(user_id, org_id, title, message, kind, link)


def notify_many(user_ids, org_id: str | None, title: str, message: str, kind: str = "INFO", link: str = "") -> None:
    for user_id in set(filter(None, user_ids)):
        notify(user_id, org_id, title, message, kind, link)


def audit(action: str, target_type: str = "", target_id: str = "", detail: str = "", org_id: str | None = None, ip: str = "") -> None:
    user = current_user()
    if not user:
        return
    operations_repo.log_action(
        actor_id=user["_id"],
        actor_role=user.get("role", ""),
        org_id=org_id if org_id is not None else user.get("organization_id"),
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
        ip=ip,
    )


def safe_log(message: str, **fields) -> None:
    """Audit-style logging with explicit fields only (never secrets)."""
    safe_fields = {k: v for k, v in fields.items() if k not in {"password", "token", "api_key"}}
    logger.info("%s %s", message, safe_fields if safe_fields else "")
