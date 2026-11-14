"""Initialize the database: indexes, catalog and the first Super Admin.

Usage:
    python scripts/initialize_database.py

Safe to run repeatedly. Catalog seeding is idempotent; demo accounts are only
created when the database is empty and SEED_DEMO_ON_START is enabled.
"""
import sys

from _bootstrap import build_app

COLLECTIONS = [
    "users",
    "organizations",
    "departments",
    "approval_requests",
    "learner_profiles",
    "skills",
    "career_roles",
    "learning_resources",
    "assessment_questions",
    "assessments",
    "assessment_attempts",
    "roadmaps",
    "notifications",
    "audit_logs",
    "ai_agent_executions",
    "trainer_assignments",
    "trainer_feedback",
]


def main() -> int:
    app = build_app()
    with app.app_context():
        from app.database.mongo import get_db
        from app.database.seed import ensure_super_admin

        db = get_db()
        ensure_super_admin(app)

        print(f"Database mode: {app.extensions.get('db_mode')}")
        print("Collections:")
        for name in COLLECTIONS:
            print(f"  {name}: {db[name].count_documents({})}")

        from app.repositories import catalog_repo

        print(
            "Catalog: "
            f"{len(catalog_repo.list_skills())} skills, "
            f"{len(catalog_repo.list_careers(active_only=False))} careers, "
            f"{len(catalog_repo.list_resources(limit=500))} resources, "
            f"{catalog_repo.count_questions()} questions"
        )
        print("Initialization complete.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
