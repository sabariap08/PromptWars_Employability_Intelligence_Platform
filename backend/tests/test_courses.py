"""Course catalog, enrolment progress, recommendations and leaderboard."""
from conftest import login, post


def test_course_catalog_and_enrolment(client):
    token = login(client, "aarav@eip.local")
    catalog = client.get("/api/learning/courses").get_json()["data"]
    assert catalog["total"] >= 10
    course = catalog["courses"][0]
    assert "modules" not in course

    detail = client.get(f"/api/learning/courses/{course['_id']}").get_json()["data"]["course"]
    assert len(detail["modules"]) == 3

    enrolled = post(client, f"/api/learning/courses/{course['_id']}/enroll", {}, token)
    assert enrolled.status_code == 201
    enrollment = enrolled.get_json()["data"]["enrollment"]
    assert enrollment["status"] == "ENROLLED"

    again = post(client, f"/api/learning/courses/{course['_id']}/enroll", {}, token)
    assert again.status_code == 200
    assert again.get_json()["data"]["already_enrolled"] is True

    mine = client.get("/api/learning/enrollments").get_json()["data"]["courses"]
    assert any(item["_id"] == course["_id"] for item in mine)

    for index, module in enumerate(detail["modules"]):
        progress = post(
            client,
            f"/api/learning/enrollments/{enrollment['_id']}/progress",
            {"module_id": module["id"], "completed": True},
            token,
        )
        assert progress.status_code == 200
        current = progress.get_json()["data"]["course"]
        assert current["enrollment"]["progress"] == round((index + 1) / 3 * 100)
    assert current["enrollment"]["status"] == "COMPLETED"

    recommended = client.get("/api/learning/recommended-courses").get_json()["data"]["courses"]
    assert isinstance(recommended, list)


def test_leaderboard_includes_current_learner(client):
    login(client, "aarav@eip.local")
    data = client.get("/api/learning/leaderboard").get_json()["data"]
    assert data["scope"] == "organization"
    assert data["total"] >= 1
    assert data["me"] is not None
    assert data["me"]["rank"] >= 1
    assert data["leaderboard"][0]["points"] >= data["leaderboard"][-1]["points"]


def test_course_detail_and_progress_validation(client):
    token = login(client, "aarav@eip.local")
    missing = client.get("/api/learning/courses/does-not-exist")
    assert missing.status_code == 404
    assert missing.get_json()["error_code"] == "COURSE_NOT_FOUND"
    invalid = post(client, "/api/learning/enrollments/does-not-exist/progress", {"module_id": "x"}, token)
    assert invalid.status_code == 404
    assert invalid.get_json()["error_code"] == "ENROLLMENT_NOT_FOUND"


def test_admin_course_update_preserves_module_ids(client):
    token = login(client, "superadmin@eip.local")
    created = post(
        client,
        "/api/admin/courses",
        {"title": "QA Course", "provider": "EIP", "modules": ["Module A", "Module B"]},
        token,
    )
    assert created.status_code == 201
    course = created.get_json()["data"]
    module_ids = [module["id"] for module in course["modules"]]

    response = client.put(
        f"/api/admin/courses/{course['_id']}",
        json={
            "title": "QA Course",
            "provider": "EIP",
            "modules": ["Module A", "Module B"],
            "is_active": False,
        },
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 200
    updated = response.get_json()["data"]
    assert [module["id"] for module in updated["modules"]] == module_ids
    assert updated["is_active"] is False
