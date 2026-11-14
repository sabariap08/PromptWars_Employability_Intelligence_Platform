"""Server-rendered pages. Data is loaded through the JSON API."""
from flask import Blueprint, redirect, render_template, request, url_for

from app.security.auth import (
    ADMIN_ROLES,
    LEARNER_ROLES,
    ROLE_ORGANIZATION_ADMIN,
    ROLE_SUPER_ADMIN,
    ROLE_UNIVERSITY_ADMIN,
    current_user,
    page_login_required,
    page_roles_required,
)

bp = Blueprint("pages", __name__)

ORG_ADMIN = (ROLE_UNIVERSITY_ADMIN, ROLE_ORGANIZATION_ADMIN)


@bp.get("/")
def landing():
    if current_user():
        return redirect(url_for("pages.dashboard_router"))
    return render_template("landing.html")


@bp.get("/login")
def login_page():
    if current_user():
        return redirect(url_for("pages.dashboard_router"))
    return render_template("auth/login.html", next_url=request.args.get("next", ""))


@bp.get("/register")
def register_page():
    return redirect(url_for("pages.register_student_page"))


@bp.get("/register/student")
def register_student_page():
    return render_template("auth/register.html", mode="student")


@bp.get("/register/employee")
def register_employee_page():
    return render_template("auth/register.html", mode="employee")


@bp.get("/register/university")
def register_university_page():
    return render_template("auth/register.html", mode="university")


@bp.get("/register/organization")
def register_organization_page():
    return render_template("auth/register.html", mode="organization")


@bp.get("/verify-email")
def verify_email_page():
    return render_template(
        "auth/verify_email.html",
        token=request.args.get("token", ""),
        email=request.args.get("email", ""),
    )


@bp.get("/pending")
def pending_page():
    return render_template("auth/pending.html")


@bp.get("/app")
def dashboard_router():
    user = current_user()
    if not user:
        return redirect(url_for("pages.login_page", next=request.path))
    role = user.get("role")
    if role == ROLE_SUPER_ADMIN:
        return redirect(url_for("pages.platform_page"))
    if role in ORG_ADMIN:
        return redirect(url_for("pages.admin_page"))
    return redirect(url_for("pages.learner_dashboard"))


@bp.get("/app/dashboard")
@page_roles_required(*LEARNER_ROLES)
def learner_dashboard():
    return render_template("app/dashboard.html")


@bp.get("/app/profile")
@page_roles_required(*LEARNER_ROLES)
def profile_page():
    return render_template("app/profile.html")


@bp.get("/app/assessments")
@page_roles_required(*LEARNER_ROLES)
def assessments_page():
    return render_template("app/assessments.html")


@bp.get("/app/roadmap")
@page_roles_required(*LEARNER_ROLES)
def roadmap_page():
    return render_template("app/roadmap.html")


@bp.get("/app/skills")
@page_roles_required(*LEARNER_ROLES)
def skills_page():
    return render_template("app/skills.html")


@bp.get("/app/projects")
@page_roles_required(*LEARNER_ROLES)
def projects_page():
    return render_template("app/projects.html")


@bp.get("/app/courses")
@page_roles_required(*LEARNER_ROLES)
def courses_page():
    return render_template("app/courses.html")


@bp.get("/app/leaderboard")
@page_roles_required(*LEARNER_ROLES)
def leaderboard_page():
    return render_template("app/leaderboard.html")


@bp.get("/app/readiness")
@page_roles_required(*LEARNER_ROLES)
def readiness_page():
    return render_template("app/readiness.html")


@bp.get("/app/mentor")
@page_roles_required(*LEARNER_ROLES)
def mentor_page():
    return render_template("app/mentor.html")


@bp.get("/app/notifications")
@page_login_required
def notifications_page():
    return render_template("app/notifications.html")


@bp.get("/app/admin")
@page_roles_required(*ORG_ADMIN)
def admin_page():
    return render_template("app/admin.html")


@bp.get("/app/requests")
@page_roles_required(*ORG_ADMIN)
def requests_page():
    return render_template("app/requests.html")


@bp.get("/app/content")
@page_roles_required(*ADMIN_ROLES)
def content_page():
    return render_template("app/content.html")


@bp.get("/app/platform")
@page_roles_required(ROLE_SUPER_ADMIN)
def platform_page():
    return render_template("app/platform.html")


@bp.get("/app/organizations")
@page_roles_required(ROLE_SUPER_ADMIN)
def organizations_page():
    return render_template("app/organizations.html")


@bp.get("/app/agents")
@page_roles_required(ROLE_SUPER_ADMIN)
def agents_page():
    return render_template("app/agents.html")


@bp.get("/app/settings")
@page_roles_required(ROLE_SUPER_ADMIN)
def settings_page():
    return render_template("app/settings.html")
