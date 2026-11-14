"""Authentication: pages, login, CSRF, registration and verification."""
from urllib.parse import parse_qs, urlparse

from conftest import csrf, login, post


def test_public_pages_load(client):
    assert client.get("/").status_code == 200
    assert client.get("/login").status_code == 200
    assert client.get("/register", follow_redirects=True).status_code == 200


def test_login_and_me(client):
    login(client, "aarav@eip.local")
    payload = client.get("/api/auth/me").get_json()["data"]
    assert payload["user"]["email"] == "aarav@eip.local"
    assert payload["user"]["role"] == "STUDENT"
    assert payload["organization"]["name"] == "Rathinam Technical Campus"


def test_login_rejects_bad_password(client):
    token = csrf(client)
    response = post(client, "/api/auth/login", {"email": "aarav@eip.local", "password": "wrong-pass1"}, token)
    assert response.status_code == 401
    assert response.get_json()["error_code"] == "INVALID_CREDENTIALS"


def test_login_requires_csrf(client):
    response = client.post("/api/auth/login", json={"email": "aarav@eip.local", "password": "Demo@12345"})
    assert response.status_code == 403
    assert response.get_json()["error_code"] == "CSRF_FAILED"


def test_unknown_email_does_not_leak(client):
    token = csrf(client)
    known = post(client, "/api/auth/login", {"email": "aarav@eip.local", "password": "nope-nope1"}, token)
    token = csrf(client)
    unknown = post(client, "/api/auth/login", {"email": "ghost@eip.local", "password": "nope-nope1"}, token)
    assert known.status_code == unknown.status_code == 401
    assert known.get_json()["message"] == unknown.get_json()["message"]


def test_organization_registration_and_verification(app):
    client = app.test_client()
    token = csrf(client)
    payload = {
        "name": "Test Institute of Technology",
        "official_email": "office@testinstitute.demo",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "country": "India",
        "admin_name": "Test Admin",
        "admin_email": "admin@testinstitute.demo",
        "password": "StrongPass123",
        "confirm_password": "StrongPass123",
        "registration_identifier": "TEST-UNI-001",
    }
    response = post(client, "/api/auth/register/university", payload, token)
    assert response.status_code == 201, response.get_json()
    data = response.get_json()["data"]
    assert data["organization"]["approval_status"] == "PENDING_APPROVAL"
    assert data["verification"]["required"] is True
    dev_link = data["verification"]["dev_link"]
    raw_token = parse_qs(urlparse(dev_link).query)["token"][0]

    token = csrf(client)
    verified = post(client, "/api/auth/verify-email", {"token": raw_token}, token)
    assert verified.status_code == 200

    pending_login = post(
        client,
        "/api/auth/login",
        {"email": "admin@testinstitute.demo", "password": "StrongPass123"},
        csrf(client),
    )
    assert pending_login.status_code == 403
    assert pending_login.get_json()["error_code"] == "ACCOUNT_NOT_ACTIVE"


def test_logout_clears_session(client):
    login(client, "aarav@eip.local")
    token = csrf(client)
    logout = post(client, "/api/auth/logout", {}, token)
    assert logout.status_code == 200
    assert client.get("/api/auth/me").status_code == 401
