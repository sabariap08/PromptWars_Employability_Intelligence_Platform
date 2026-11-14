"""Seed clearly-labelled demo organizations, accounts and learner evidence.

Usage:
    python scripts/seed_demo_data.py

Demo data is only created when the users collection is empty. This prevents
duplicates and protects real deployments. Demo accounts all use the password
Demo@12345 (development only).
"""
import sys

from _bootstrap import build_app

DEMO_ACCOUNTS = [
    ("Super Admin", "superadmin@eip.local"),
    ("University admin", "rathinam.admin@eip.local"),
    ("Organization admin", "nova.admin@eip.local"),
    ("Expert reviewer", "employee@eip.local"),
    ("Student", "aarav@eip.local"),
]


def main() -> int:
    app = build_app()
    with app.app_context():
        from app.database.seed import _seed_demo
        from app.repositories import users_repo

        if users_repo.count() > 0:
            print("Users already exist; demo seeding skipped to avoid duplicates.")
        else:
            _seed_demo(app)
            print("Demo data seeded.")

        print(f"Database mode: {app.extensions.get('db_mode')}")
        if app.extensions.get("db_mode") == "memory":
            print("NOTE: memory mode is not persistent. Set MONGODB_URI for a durable database.")
        print("Demo accounts (password: Demo@12345):")
        for label, email in DEMO_ACCOUNTS:
            exists = "yes" if users_repo.find_by_email(email) else "no"
            print(f"  {label:20} {email:28} exists={exists}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
