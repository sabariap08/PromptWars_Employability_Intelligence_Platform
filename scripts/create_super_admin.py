"""Create (or reset) the platform Super Admin account.

Usage:
    python scripts/create_super_admin.py
    python scripts/create_super_admin.py --email owner@example.com --password "StrongPass123"
    python scripts/create_super_admin.py --email owner@example.com --reset-password
"""
import argparse
import os
import sys

from _bootstrap import build_app


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or update the EIP Super Admin account.")
    parser.add_argument("--email", default=os.environ.get("SUPER_ADMIN_EMAIL", "superadmin@eip.local"))
    parser.add_argument("--password", default=os.environ.get("SUPER_ADMIN_PASSWORD", ""))
    parser.add_argument("--name", default=os.environ.get("SUPER_ADMIN_NAME", "Platform Owner"))
    parser.add_argument("--reset-password", action="store_true", help="Reset the password if the account exists.")
    args = parser.parse_args()

    email = args.email.strip().lower()
    if not email or "@" not in email:
        print("A valid --email is required.")
        return 2

    from app.repositories import users_repo
    from app.security.passwords import hash_password
    from app.utils.ids import now_utc

    app = build_app()
    with app.app_context():
        existing = users_repo.find_by_email(email)
        if existing:
            if args.reset_password:
                if not args.password:
                    print("--reset-password requires --password (or SUPER_ADMIN_PASSWORD).")
                    return 2
                users_repo.update_user(
                    existing["_id"],
                    {
                        "password_hash": hash_password(args.password),
                        "role": "SUPER_ADMIN",
                        "account_status": "APPROVED",
                        "email_verified": True,
                        "email_verification_token": None,
                    },
                )
                print(f"Password reset for Super Admin {email}.")
            else:
                print(f"Super Admin already exists: {email} (use --reset-password to change it).")
            return 0

        password = args.password
        if not password:
            print("No password supplied. Set SUPER_ADMIN_PASSWORD or pass --password.")
            return 2
        if len(password) < 8 or not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
            print("Password must be at least 8 characters and include a letter and a number.")
            return 2

        user = users_repo.create_user(
            {
                "full_name": args.name.strip() or "Platform Owner",
                "email": email,
                "password_hash": hash_password(password),
                "role": "SUPER_ADMIN",
                "account_status": "APPROVED",
                "email_verified": True,
                "approved_at": now_utc(),
            }
        )
        print(f"Created Super Admin {user['email']} ({user['_id']}).")
        print(f"Database mode: {app.extensions.get('db_mode')}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
