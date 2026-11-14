"""Tenant isolation, role guards and expert-review authorization."""
from conftest import csrf, login, post


def _user_id(client):
    return client.get("/api/auth/me").get_json()["data"]["user"]["_id"]


def test_student_cannot_reach_admin_surfaces(app):
    student = app.test_client()
    login(student, "aarav@eip.local")
    assert student.get("/api/approvals/members").status_code == 403
    assert student.get("/api/organizations/me").status_code == 403
    assert student.get("/api/admin/overview").status_code == 403
    assert student.get("/api/admin/executions").status_code == 403
    assert student.get("/api/learner/expert/learners").status_code == 403


def test_cross_organization_snapshot_is_forbidden(app):
    student = app.test_client()
    login(student, "aarav@eip.local")
    student_id = _user_id(student)

    company_admin = app.test_client()
    login(company_admin, "nova.admin@eip.local")
    blocked = company_admin.get(f"/api/admin/learner/{student_id}")
    assert blocked.status_code == 403
    assert blocked.get_json()["error_code"] == "FORBIDDEN"

    university_admin = app.test_client()
    login(university_admin, "rathinam.admin@eip.local")
    allowed = university_admin.get(f"/api/admin/learner/{student_id}")
    assert allowed.status_code == 200
    assert allowed.get_json()["data"]["user"]["email"] == "aarav@eip.local"


def test_expert_review_requires_assignment(app):
    expert = app.test_client()
    login(expert, "employee@eip.local")
    learners = expert.get("/api/learner/expert/learners").get_json()["data"]["learners"]
    assert learners, "the seed assigns the demo student to the demo expert"
    learner_id = learners[0]["_id"]

    detail = expert.get(f"/api/learner/expert/learners/{learner_id}")
    assert detail.status_code == 200
    assert "skills" in detail.get_json()["data"]

    token = csrf(expert)
    feedback = post(
        expert,
        "/api/learner/expert/feedback",
        {"learner_id": learner_id, "skill_name": "Python", "rating": 4, "feedback": "Solid project evidence."},
        token,
    )
    assert feedback.status_code == 201, feedback.get_json()
    assert feedback.get_json()["data"]["feedback"]["rating"] == 4

    random_id = "does-not-exist"
    blocked = expert.get(f"/api/learner/expert/learners/{random_id}")
    assert blocked.status_code == 403


def test_super_admin_global_access(app):
    admin = app.test_client()
    login(admin, "superadmin@eip.local")
    assert admin.get("/api/admin/overview").status_code == 200
    assert admin.get("/api/admin/organizations").status_code == 200
    assert admin.get("/api/admin/agents").status_code == 200
    assert admin.get("/api/approvals/organizations?status=PENDING_APPROVAL").status_code == 200
