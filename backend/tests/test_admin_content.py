"""Admin content entry points and shared creation permissions."""
from conftest import login, post

ADMIN_ACCOUNTS = [
    "superadmin@eip.local",
    "rathinam.admin@eip.local",
    "nova.admin@eip.local",
]


def test_all_admins_can_add_courses_and_questions(app):
    for email in ADMIN_ACCOUNTS:
        client = app.test_client()
        token = login(client, email)
        course = post(
            client,
            "/api/admin/courses",
            {"title": "Shared course " + email, "provider": "EIP", "modules": ["Intro", "Practice"]},
            token,
        )
        assert course.status_code == 201, course.get_json()

        question = post(
            client,
            "/api/admin/catalog/questions",
            {
                "skill_name": "Python",
                "question_type": "FACTUAL",
                "difficulty": "EASY",
                "prompt": "Which keyword defines a function?",
                "options": "def|class|import|return",
                "correct_option": "A",
            },
            token,
        )
        assert question.status_code == 201, question.get_json()


def test_admin_navigation_links_to_content_page(app):
    for email in ["rathinam.admin@eip.local", "nova.admin@eip.local"]:
        client = app.test_client()
        login(client, email)
        admin_html = client.get("/app/admin").get_data(as_text=True)
        assert "Learners &amp; experts" not in admin_html
        assert "/app/content" in admin_html
        assert "Add course" in admin_html
        assert "Add questions" in admin_html
        assert client.get("/app/content").status_code == 200

    super_admin = app.test_client()
    login(super_admin, "superadmin@eip.local")
    platform_html = super_admin.get("/app/platform").get_data(as_text=True)
    assert "/app/content" in platform_html
    assert "Add course" in platform_html
    assert "Add questions" in platform_html

    student = app.test_client()
    login(student, "aarav@eip.local")
    assert student.get("/app/content").status_code == 302
