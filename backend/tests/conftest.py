"""Pytest fixtures: isolated in-memory app, API client helpers and logins."""
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app import create_app

DEMO_PASSWORD = "Demo@12345"


@pytest.fixture()
def app():
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "MONGODB_URI": "",
            "SEED_DEMO_ON_START": True,
            "RATELIMIT_ENABLED": False,
            "EXPOSE_VERIFICATION_LINK": True,
            "SESSION_COOKIE_SECURE": False,
            "EMAIL_DELIVERY": "console",
            "MAIL_SERVER": "",
            "MAIL_USERNAME": "",
            "MAIL_PASSWORD": "",
            "MAIL_FROM": "no-reply@eip.local",
            "GROQ_API_KEY": "",
            "GEMINI_API_KEY": "",
            "OPENROUTER_API_KEY": "",
            "HF_API_KEY": "",
            "OLLAMA_ENABLED": False,
            "OLLAMA_API_KEY": "",
        }
    )
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


def csrf(client):
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    return response.get_json()["data"]["csrf_token"]


def post(client, path, payload=None, token=None):
    headers = {"X-CSRF-Token": token} if token else {}
    return client.post(path, json=payload or {}, headers=headers)


def login(client, email, password=DEMO_PASSWORD):
    token = csrf(client)
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()["data"]["csrf_token"]


@pytest.fixture()
def login_as(client):
    def _login(email, password=DEMO_PASSWORD):
        return login(client, email, password)

    return _login
