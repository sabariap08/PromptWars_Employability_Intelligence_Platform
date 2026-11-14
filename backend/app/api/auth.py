"""Authentication endpoints: CSRF, registration, verification, session."""
from flask import Blueprint, request

from app.api.common import json_body
from app.repositories import organizations_repo
from app.security.auth import api_login_required, current_user
from app.security.csrf import get_csrf_token
from app.security.rate_limit import limiter
from app.services import auth_service
from app.utils.responses import ok

bp = Blueprint("auth_api", __name__, url_prefix="/api/auth")


@bp.get("/csrf")
def csrf_token():
    return ok({"csrf_token": get_csrf_token(), "authenticated": bool(current_user())})


@bp.get("/me")
@api_login_required
def me():
    user = current_user()
    organization = organizations_repo.find_org(user.get("organization_id")) if user.get("organization_id") else None
    department = (
        organizations_repo.find_department(user.get("department_id")) if user.get("department_id") else None
    )
    return ok(
        {
            "user": user,
            "organization": organization,
            "department": department,
            "csrf_token": get_csrf_token(),
        }
    )


@bp.post("/register/student")
@limiter.limit("8 per minute")
def register_student():
    result = auth_service.register_student(json_body())
    return ok(result, result.get("message", "Registration submitted."), 201)


@bp.post("/register/employee")
@limiter.limit("8 per minute")
def register_employee():
    result = auth_service.register_employee(json_body())
    return ok(result, result.get("message", "Registration submitted."), 201)


@bp.post("/register/university")
@limiter.limit("6 per minute")
def register_university():
    result = auth_service.register_organization_admin(json_body(), "UNIVERSITY")
    return ok(result, result.get("message", "Registration submitted."), 201)


@bp.post("/register/organization")
@limiter.limit("6 per minute")
def register_organization():
    result = auth_service.register_organization_admin(json_body(), "COMPANY")
    return ok(result, result.get("message", "Registration submitted."), 201)


@bp.post("/verify-email")
@limiter.limit("15 per minute")
def verify_email():
    token = json_body().get("token") or request.args.get("token", "")
    result = auth_service.verify_email(token)
    return ok(result, "Your email address is verified.")


@bp.post("/login")
@limiter.limit("12 per minute")
def login():
    data = json_body()
    result = auth_service.login(data.get("email", ""), data.get("password", ""))
    result["csrf_token"] = get_csrf_token()
    return ok(result, "Signed in successfully.")


@bp.post("/logout")
def logout():
    auth_service.logout()
    return ok({"csrf_token": get_csrf_token()}, "You have been signed out.")
