"""Two-level approvals: organization registration and member membership."""
from urllib.parse import parse_qs, urlparse

from conftest import DEMO_PASSWORD, csrf, login, post


def _verify(client, dev_link):
    raw_token = parse_qs(urlparse(dev_link).query)["token"][0]
    token = csrf(client)
    response = post(client, "/api/auth/verify-email", {"token": raw_token}, token)
    assert response.status_code == 200


def test_super_admin_approves_new_organization(app):
    applicant = app.test_client()
    token = csrf(applicant)
    response = post(
        applicant,
        "/api/auth/register/university",
        {
            "name": "Approval Test University",
            "official_email": "office@approvaltest.demo",
            "city": "Madurai",
            "state": "Tamil Nadu",
            "country": "India",
            "admin_name": "Approval Admin",
            "admin_email": "admin@approvaltest.demo",
            "password": "StrongPass123",
            "confirm_password": "StrongPass123",
        },
        token,
    )
    assert response.status_code == 201
    _verify(applicant, response.get_json()["data"]["verification"]["dev_link"])

    super_admin = app.test_client()
    login(super_admin, "superadmin@eip.local")
    token = csrf(super_admin)
    listing = super_admin.get("/api/approvals/organizations?status=PENDING_APPROVAL").get_json()["data"]
    match = [org for org in listing["organizations"] if org["name"] == "Approval Test University"]
    assert match
    org_id = match[0]["_id"]
    approved = post(super_admin, f"/api/approvals/organizations/{org_id}/approve", {}, token)
    assert approved.status_code == 200
    assert approved.get_json()["data"]["approval_status"] == "APPROVED"

    login(applicant, "admin@approvaltest.demo", "StrongPass123")
    me = applicant.get("/api/auth/me").get_json()["data"]
    assert me["user"]["account_status"] == "APPROVED"
    assert me["organization"]["approval_status"] == "APPROVED"


def test_university_admin_approves_student(app):
    admin_client = app.test_client()
    login(admin_client, "rathinam.admin@eip.local")
    context = admin_client.get("/api/organizations/me").get_json()["data"]
    department_id = context["departments"][0]["_id"]

    student = app.test_client()
    token = csrf(student)
    response = post(
        student,
        "/api/auth/register/student",
        {
            "full_name": "New Student",
            "email": "new.student@eip.local",
            "password": "StrongPass123",
            "confirm_password": "StrongPass123",
            "phone": "+91 90000 12345",
            "organization_id": context["organization"]["_id"],
            "department_id": department_id,
            "degree": "B.E. CSE",
            "academic_year": "2024-2028",
            "year_of_study": "2",
            "roll_number": "24CSE999",
        },
        token,
    )
    assert response.status_code == 201, response.get_json()
    _verify(student, response.get_json()["data"]["verification"]["dev_link"])

    pending = post(
        student,
        "/api/auth/login",
        {"email": "new.student@eip.local", "password": "StrongPass123"},
        csrf(student),
    )
    assert pending.status_code == 403
    assert pending.get_json()["error_code"] == "ACCOUNT_NOT_ACTIVE"

    members = admin_client.get("/api/approvals/members?status=PENDING_APPROVAL").get_json()["data"]["members"]
    match = [member for member in members if member["email"] == "new.student@eip.local"]
    assert match
    token = csrf(admin_client)
    approved = post(admin_client, f"/api/approvals/members/{match[0]['_id']}/approve", {}, token)
    assert approved.status_code == 200

    login(student, "new.student@eip.local", "StrongPass123")
    me = student.get("/api/auth/me").get_json()["data"]
    assert me["user"]["account_status"] == "APPROVED"
    assert me["user"]["role"] == "STUDENT"


def test_demo_student_can_login(app):
    client = app.test_client()
    login(client, "aarav@eip.local", DEMO_PASSWORD)
    assert client.get("/api/learner/dashboard").status_code == 200
