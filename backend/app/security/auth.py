"""Session authentication, role guards and tenant scoping helpers."""
from functools import wraps

from flask import g, redirect, request, session, url_for

from app.repositories import users_repo
from app.utils.responses import AppError

ROLE_SUPER_ADMIN = "SUPER_ADMIN"
ROLE_UNIVERSITY_ADMIN = "UNIVERSITY_ADMIN"
ROLE_ORGANIZATION_ADMIN = "ORGANIZATION_ADMIN"
ROLE_STUDENT = "STUDENT"
ROLE_EMPLOYEE = "EMPLOYEE"

LEARNER_ROLES = (ROLE_STUDENT, ROLE_EMPLOYEE)
ADMIN_ROLES = (ROLE_SUPER_ADMIN, ROLE_UNIVERSITY_ADMIN, ROLE_ORGANIZATION_ADMIN)


def public_user(user: dict | None) -> dict | None:
    if not user:
        return None
    clean = {k: v for k, v in user.items() if k not in {"password_hash", "email_verification_token"}}
    return clean


def current_user() -> dict | None:
    if "current_user" in g:
        return g.current_user
    user_id = session.get("user_id")
    user = users_repo.find_by_id(user_id) if user_id else None
    if user and user.get("account_status") != "APPROVED":
        user = None
        session.clear()
    user = public_user(user)
    g.current_user = user
    return user


def login_user(user_id: str) -> None:
    session.clear()
    session["user_id"] = user_id
    session.permanent = True
    g.pop("current_user", None)


def logout_user() -> None:
    session.clear()
    g.pop("current_user", None)


def api_login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user():
            raise AppError("Please sign in to continue.", "AUTH_REQUIRED", 401)
        return view(*args, **kwargs)

    return wrapper


def api_roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                raise AppError("Please sign in to continue.", "AUTH_REQUIRED", 401)
            if user.get("role") not in roles:
                raise AppError("You do not have permission to perform this action.", "FORBIDDEN", 403)
            return view(*args, **kwargs)

        return wrapper

    return decorator


def page_login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect(url_for("pages.login_page", next=request.path))
        return view(*args, **kwargs)

    return wrapper


def page_roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for("pages.login_page", next=request.path))
            if user.get("role") not in roles:
                return redirect(url_for("pages.dashboard_router"))
            return view(*args, **kwargs)

        return wrapper

    return decorator


def require_org_access(org_id: str) -> None:
    """Admins may only touch their own organization; Super Admin is global."""
    user = current_user()
    if not user:
        raise AppError("Please sign in to continue.", "AUTH_REQUIRED", 401)
    if user["role"] == ROLE_SUPER_ADMIN:
        return
    if user.get("organization_id") != org_id:
        raise AppError("You cannot access another organization's data.", "FORBIDDEN", 403)


def require_admin_for_org(org_type: str):
    """Allowed admin role for a given organization type."""
    return ROLE_UNIVERSITY_ADMIN if org_type == "UNIVERSITY" else ROLE_ORGANIZATION_ADMIN
