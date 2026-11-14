"""Agents, orchestration logging, provider routing and catalog admin."""
from conftest import csrf, login, post


def test_agent_registry_and_workflows(app):
    admin = app.test_client()
    login(admin, "superadmin@eip.local")
    data = admin.get("/api/admin/agents").get_json()["data"]
    assert len(data["agents"]) == 7
    assert "assessment.submitted" in data["workflows"]
    assert len(data["workflows"]["assessment.submitted"]) >= 3


def test_provider_routing_validation(app):
    admin = app.test_client()
    login(admin, "superadmin@eip.local")
    token = csrf(admin)

    invalid = admin.put(
        "/api/admin/providers",
        json={"primary_provider": "not-a-provider", "fallback_order": ""},
        headers={"X-CSRF-Token": token},
    )
    assert invalid.status_code == 422
    assert invalid.get_json()["error_code"] == "INVALID_PROVIDER"

    saved = admin.put(
        "/api/admin/providers",
        json={"primary_provider": "groq", "fallback_order": "gemini, ollama"},
        headers={"X-CSRF-Token": token},
    )
    assert saved.status_code == 200
    payload = saved.get_json()["data"]
    assert payload["order"][:2] == ["groq", "gemini"]


def test_assessment_runs_agents_and_logs_executions(app):
    student = app.test_client()
    login(student, "aarav@eip.local")
    token = csrf(student)
    assessment = post(student, "/api/assessments/baseline", {}, token).get_json()["data"]
    attempt = post(student, f"/api/assessments/{assessment['_id']}/start", {}, token).get_json()["data"]
    answers = {
        question["question_id"]: {"selected_option": "A"} for question in attempt["questions"]
    }
    submitted = post(
        student,
        f"/api/assessments/attempts/{attempt['_id']}/submit",
        {"answers": answers, "integrity": {"tab_switch_count": 0, "visibility_events": 0}},
        token,
    )
    assert submitted.status_code == 200

    admin = app.test_client()
    login(admin, "superadmin@eip.local")
    executions = admin.get("/api/admin/executions?limit=50").get_json()["data"]
    assert executions["stats"]["total"] >= 1
    assert executions["stats"]["fallback"] >= 1, "no API keys means deterministic fallback"
    assert any(run["workflow"] == "assessment.submitted" for run in executions["executions"])
    assert all(run["provider"] for run in executions["executions"])


def test_catalog_admin(app):
    admin = app.test_client()
    login(admin, "superadmin@eip.local")
    catalog = admin.get("/api/admin/catalog").get_json()["data"]
    assert catalog["counts"]["skills"] > 0
    assert catalog["counts"]["careers"] > 0
    assert catalog["counts"]["questions"] > 0

    token = csrf(admin)
    created = post(
        admin,
        "/api/admin/catalog/skills",
        {"name": "Docker", "category": "DevOps", "description": "Containerisation"},
        token,
    )
    assert created.status_code == 201
    assert created.get_json()["data"]["name"] == "Docker"

    refreshed = admin.get("/api/admin/catalog").get_json()["data"]
    assert any(skill["name"] == "Docker" for skill in refreshed["skills"])
