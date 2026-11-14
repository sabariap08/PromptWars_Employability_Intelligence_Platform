"""End-to-end learner journey: profile, readiness, assessment, roadmap."""
from conftest import csrf, login, post


def test_learner_dashboard_and_profile(client):
    login(client, "aarav@eip.local")
    dashboard = client.get("/api/learner/dashboard")
    assert dashboard.status_code == 200
    bundle = client.get("/api/learner/profile")
    assert bundle.status_code == 200
    data = bundle.get_json()["data"]
    assert data["profile"]["education"]["roll_number"] == "21CSE001"
    assert any(skill["skill_name"] == "Python" for skill in data["skills"])


def test_readiness_is_explainable(client):
    login(client, "aarav@eip.local")
    readiness = client.get("/api/learner/readiness")
    assert readiness.status_code == 200
    data = readiness.get_json()["data"]
    assert data["has_target"] is True
    assert data["career_name"] == "Full Stack Developer"
    assert 0 <= data["readiness"] <= 100
    assert data["required_count"] > 0
    assert isinstance(data["gaps"], list)


def test_assessment_lifecycle(client):
    login(client, "aarav@eip.local")
    token = csrf(client)
    baseline = post(client, "/api/assessments/baseline", {}, token)
    assert baseline.status_code == 201, baseline.get_json()
    assessment_id = baseline.get_json()["data"]["_id"]

    started = post(client, f"/api/assessments/{assessment_id}/start", {}, token)
    assert started.status_code == 201, started.get_json()
    attempt = started.get_json()["data"]
    assert attempt["status"] == "IN_PROGRESS"
    assert attempt["questions"]

    answers = {}
    for question in attempt["questions"]:
        if question["question_type"] == "PRACTICAL_WRITTEN":
            answers[question["question_id"]] = {
                "text_answer": "I would use Python and SQL, validate inputs carefully, and document trade-offs."
            }
        else:
            answers[question["question_id"]] = {"selected_option": "A"}

    submitted = post(
        client,
        f"/api/assessments/attempts/{attempt['_id']}/submit",
        {"answers": answers, "integrity": {"tab_switch_count": 0, "visibility_events": 0, "events": []}},
        token,
    )
    assert submitted.status_code == 200, submitted.get_json()
    payload = submitted.get_json()["data"]
    assert payload["attempt"]["status"] == "EVALUATED"
    assert payload["attempt"]["score"] is not None
    assert payload["workflow"], "the assessment workflow should log agent executions"

    result = client.get(f"/api/assessments/attempts/{attempt['_id']}/result")
    assert result.status_code == 200
    assert "topic_scores" in result.get_json()["data"]

    history = client.get("/api/assessments").get_json()["data"]
    assert any(item["attempts"] for item in history["assessments"])


def test_roadmap_generation_and_task_update(client):
    login(client, "aarav@eip.local")
    token = csrf(client)
    generated = post(client, "/api/learning/roadmap/generate", {}, token)
    assert generated.status_code == 201, generated.get_json()
    roadmap = generated.get_json()["data"]["roadmap"]
    tasks = [task for phase in roadmap["phases"] for task in phase["tasks"]]
    assert tasks

    first = tasks[0]
    started = post(client, f"/api/learning/tasks/{first['id']}", {"action": "START"}, token)
    assert started.status_code == 200
    updated = [task for phase in started.get_json()["data"]["roadmap"]["phases"] for task in phase["tasks"]]
    assert any(task["id"] == first["id"] and task["status"] == "IN_PROGRESS" for task in updated)

    completed = post(client, f"/api/learning/tasks/{first['id']}", {"action": "COMPLETE"}, token)
    assert completed.status_code == 200
    summary = completed.get_json()["data"]["summary"]
    assert summary["completion"] >= 0

    fetched = client.get("/api/learning/roadmap").get_json()["data"]
    assert fetched["roadmap"]["_id"] == roadmap["_id"]
    assert fetched["versions"]


def test_notifications_and_mentor(client):
    login(client, "aarav@eip.local")
    inbox = client.get("/api/notifications").get_json()["data"]
    assert "notifications" in inbox
    assert inbox["unread"] >= 1

    token = csrf(client)
    marked = post(client, "/api/notifications/read", {}, token)
    assert marked.status_code == 200
    assert marked.get_json()["data"]["unread"] == 0

    history = client.get("/api/mentor/history")
    assert history.status_code == 200
    chat = post(client, "/api/mentor/chat", {"message": "What should I focus on next?"}, token)
    assert chat.status_code == 200
    reply = chat.get_json()["data"]
    assert reply["reply"]
    assert reply["provider"]
