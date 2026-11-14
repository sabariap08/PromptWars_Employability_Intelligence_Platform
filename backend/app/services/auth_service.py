"""Registration, email verification and session login."""
import hashlib
import hmac
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

from flask import current_app, url_for

from app.repositories import organizations_repo, otp_repo, profiles_repo, users_repo
from app.security.auth import (
    ROLE_EMPLOYEE,
    ROLE_ORGANIZATION_ADMIN,
    ROLE_STUDENT,
    ROLE_SUPER_ADMIN,
    ROLE_UNIVERSITY_ADMIN,
    login_user,
    logout_user,
    public_user,
)
from app.security.passwords import hash_password, verify_password
from app.services import ops_service
from app.utils.ids import now_utc
from app.utils.responses import AppError
from app.utils.text import clean_text, is_http_url, normalize_email
from app.validators.common import require_fields, validate_email, validate_password

ORG_ADMIN_ROLE = {
    "UNIVERSITY": ROLE_UNIVERSITY_ADMIN,
    "COMPANY": ROLE_ORGANIZATION_ADMIN,
}


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _is_expired(value) -> bool:
    if not value:
        return True
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return True
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value < now_utc()


def _hash_otp(user_id: str, code: str) -> str:
    secret = current_app.config.get("SECRET_KEY", "")
    return hmac.new(
        secret.encode("utf-8"),
        f"{user_id}:{code}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _send_verification_email(user: dict, code: str) -> str:
    app = current_app
    if app.config.get("EMAIL_DELIVERY") != "smtp" or not app.config.get("MAIL_SERVER"):
        return "console"
    ttl = app.config.get("OTP_TTL_MINUTES", 10)
    try:
        message = MIMEText(
            f"Hello {user['full_name']},\n\n"
            f"Your EIP verification code is: {code}\n\n"
            f"The code expires in {ttl} minutes. If you did not create an account, ignore this email."
        )
        message["Subject"] = "Your EIP verification code"
        message["From"] = app.config.get("MAIL_FROM", "no-reply@eip.local")
        message["To"] = user["email"]
        with smtplib.SMTP(app.config["MAIL_SERVER"], app.config.get("MAIL_PORT", 587), timeout=10) as server:
            server.starttls()
            if app.config.get("MAIL_USERNAME"):
                server.login(app.config["MAIL_USERNAME"], app.config.get("MAIL_PASSWORD", ""))
            server.send_message(message)
        return "smtp"
    except Exception as exc:  # email failures must not block registration
        ops_service.safe_log("verification_email_failed", error=str(exc)[:200])
        return "console"


def _issue_verification(user: dict) -> dict:
    otp_repo.invalidate_active(user["_id"])
    code = f"{secrets.randbelow(1_000_000):06d}"
    ttl = int(current_app.config.get("OTP_TTL_MINUTES", 10))
    otp_repo.create_otp(
        {
            "user_id": user["_id"],
            "email": user["email"],
            "purpose": "EMAIL_VERIFICATION",
            "code_hash": _hash_otp(user["_id"], code),
            "expires_at": now_utc() + timedelta(minutes=ttl),
            "max_attempts": int(current_app.config.get("OTP_MAX_ATTEMPTS", 5)),
        }
    )
    users_repo.update_user(
        user["_id"],
        {
            "email_verification_expires_at": now_utc() + timedelta(minutes=ttl),
        },
    )
    delivery = _send_verification_email(user, code)
    payload = {
        "required": True,
        "channel": "email",
        "delivery": delivery,
        "expires_in_minutes": ttl,
    }
    if current_app.config.get("EXPOSE_VERIFICATION_LINK"):
        payload["dev_code"] = code
    return payload


def _notify_approvers(request: dict, title: str) -> None:
    if request["request_type"] == "ORGANIZATION":
        approvers = users_repo.list_by_role(ROLE_SUPER_ADMIN)
    else:
        approvers = users_repo.list_by_org(
            request["organization_id"],
            roles=[request["assigned_approver_role"]],
            statuses=["APPROVED"],
        )[0]
    ops_service.notify_many(
        [a["_id"] for a in approvers],
        request.get("organization_id"),
        title,
        "A new registration is waiting for your review.",
        "APPROVAL",
        "/app/requests",
    )


def _create_registration_user(data: dict, role: str, org_id: str, status: str) -> dict:
    return users_repo.create_user(
        {
            "full_name": data["full_name"],
            "email": data["email"],
            "password_hash": hash_password(data["password"]),
            "role": role,
            "organization_id": org_id,
            "department_id": data.get("department_id"),
            "phone": data.get("phone", ""),
            "designation": data.get("designation", ""),
            "account_status": status,
            "email_verified": False,
        }
    )


def register_organization_admin(payload: dict, org_type: str) -> dict:
    org_label = "university / college" if org_type == "UNIVERSITY" else "organization"
    require_fields(
        payload,
        [
            "name",
            "official_email",
            "city",
            "state",
            "country",
            "admin_name",
            "admin_email",
            "password",
            "confirm_password",
        ],
    )
    validate_email(payload["admin_email"])
    validate_password(payload["password"], payload["confirm_password"])
    admin_email = normalize_email(payload["admin_email"])
    if users_repo.find_by_email(admin_email):
        raise AppError("An account with this email already exists.", "EMAIL_EXISTS", 409)
    if organizations_repo.find_org_by_name(payload["name"]):
        raise AppError("This organization is already registered.", "ORGANIZATION_EXISTS", 409)
    identifier = clean_text(payload.get("registration_identifier"), 120)
    if identifier and organizations_repo.find_org_by_identifier(identifier):
        raise AppError("This registration identifier is already in use.", "IDENTIFIER_EXISTS", 409)
    official_email = normalize_email(payload["official_email"])
    website = clean_text(payload.get("website"), 300)
    if website and not is_http_url(website):
        raise AppError("Website must start with http:// or https://.", "INVALID_WEBSITE", 422)

    org = organizations_repo.create_org(
        {
            "name": clean_text(payload["name"], 160),
            "organization_type": org_type,
            "subtype": clean_text(payload.get("subtype"), 120),
            "industry": clean_text(payload.get("industry"), 120),
            "location": {
                "country": clean_text(payload.get("country"), 80),
                "state": clean_text(payload.get("state"), 80),
                "district": clean_text(payload.get("district"), 80),
                "city": clean_text(payload.get("city"), 80),
            },
            "official_email": official_email,
            "website": website,
            "contact_number": clean_text(payload.get("contact_number"), 40),
            "address": clean_text(payload.get("address"), 400),
            "registration_identifier": identifier,
            "verification_documents": payload.get("verification_documents", []),
            "approval_status": "PENDING_APPROVAL",
        }
    )

    admin = _create_registration_user(
        {
            "full_name": clean_text(payload["admin_name"], 120),
            "email": admin_email,
            "password": payload["password"],
            "phone": clean_text(payload.get("admin_phone"), 40),
            "designation": clean_text(payload.get("admin_designation"), 120),
        },
        ORG_ADMIN_ROLE[org_type],
        org["_id"],
        "PENDING_APPROVAL",
    )

    request = organizations_repo.create_approval_request(
        {
            "request_type": "ORGANIZATION",
            "applicant_user_id": admin["_id"],
            "organization_id": org["_id"],
            "requested_role": ORG_ADMIN_ROLE[org_type],
            "assigned_approver_role": ROLE_SUPER_ADMIN,
        }
    )
    _notify_approvers(request, f"New {org_label} registration pending")
    ops_service.safe_log("organization_registered", organization_id=org["_id"], org_type=org_type)

    verification = _issue_verification(admin)
    return {
        "user": public_user(admin),
        "organization": {"_id": org["_id"], "name": org["name"], "approval_status": org["approval_status"]},
        "verification": verification,
        "message": (
            "Your registration has been submitted. Verify your email, then our platform team "
            "will review your organization."
        ),
    }


def _validate_approved_org(org_id: str, expected_type: str) -> dict:
    org = organizations_repo.find_org(org_id)
    if not org or org.get("organization_type") != expected_type:
        raise AppError("Please select a valid organization.", "ORGANIZATION_NOT_FOUND", 404)
    if org.get("approval_status") != "APPROVED":
        raise AppError(
            "That organization is not currently accepting registrations.",
            "ORGANIZATION_NOT_APPROVED",
            422,
        )
    return org


def _validate_department(org_id: str, department_id: str) -> dict:
    department = organizations_repo.find_department(department_id)
    if not department or department.get("organization_id") != org_id:
        raise AppError("Please select a valid department.", "DEPARTMENT_NOT_FOUND", 404)
    return department


def register_student(payload: dict) -> dict:
    require_fields(
        payload,
        [
            "full_name",
            "email",
            "password",
            "confirm_password",
            "phone",
            "organization_id",
            "degree",
            "academic_year",
            "year_of_study",
            "roll_number",
        ],
    )
    validate_email(payload["email"])
    validate_password(payload["password"], payload["confirm_password"])
    email = normalize_email(payload["email"])
    if users_repo.find_by_email(email):
        raise AppError("An account with this email already exists.", "EMAIL_EXISTS", 409)
    org = _validate_approved_org(payload["organization_id"], "UNIVERSITY")
    department_id = clean_text(payload.get("department_id"), 80)
    department = _validate_department(org["_id"], department_id) if department_id else None

    user = _create_registration_user(
        {
            "full_name": clean_text(payload["full_name"], 120),
            "email": email,
            "password": payload["password"],
            "phone": clean_text(payload["phone"], 40),
            "department_id": department["_id"] if department else None,
        },
        ROLE_STUDENT,
        org["_id"],
        "EMAIL_VERIFICATION_PENDING",
    )
    profiles_repo.create_profile(
        user["_id"],
        org["_id"],
        "STUDENT",
        education={
            "degree": clean_text(payload["degree"], 120),
            "academic_year": clean_text(payload["academic_year"], 40),
            "year_of_study": clean_text(payload["year_of_study"], 40),
            "roll_number": clean_text(payload["roll_number"], 60),
            "department_name": department["name"] if department else "",
        },
    )
    request = organizations_repo.create_approval_request(
        {
            "request_type": "MEMBERSHIP",
            "applicant_user_id": user["_id"],
            "organization_id": org["_id"],
            "requested_role": ROLE_STUDENT,
            "assigned_approver_role": ROLE_UNIVERSITY_ADMIN,
        }
    )
    _notify_approvers(request, "New student registration pending")
    verification = _issue_verification(user)
    return {
        "user": public_user(user),
        "organization": {"_id": org["_id"], "name": org["name"]},
        "department": {"_id": department["_id"], "name": department["name"]} if department else None,
        "verification": verification,
        "message": (
            "Your registration has been submitted. Verify your email, then your institution "
            "administrator will approve your account."
        ),
    }


def register_employee(payload: dict) -> dict:
    require_fields(
        payload,
        [
            "full_name",
            "email",
            "password",
            "confirm_password",
            "phone",
            "organization_id",
            "department_id",
            "designation",
            "employment_type",
            "years_experience",
        ],
    )
    validate_email(payload["email"])
    validate_password(payload["password"], payload["confirm_password"])
    email = normalize_email(payload["email"])
    if users_repo.find_by_email(email):
        raise AppError("An account with this email already exists.", "EMAIL_EXISTS", 409)
    org = _validate_approved_org(payload["organization_id"], "COMPANY")
    department = _validate_department(org["_id"], payload["department_id"])

    user = _create_registration_user(
        {
            "full_name": clean_text(payload["full_name"], 120),
            "email": email,
            "password": payload["password"],
            "phone": clean_text(payload["phone"], 40),
            "designation": clean_text(payload["designation"], 120),
            "department_id": department["_id"],
        },
        ROLE_EMPLOYEE,
        org["_id"],
        "EMAIL_VERIFICATION_PENDING",
    )
    profiles_repo.create_profile(
        user["_id"],
        org["_id"],
        "EMPLOYEE",
        employment={
            "designation": clean_text(payload["designation"], 120),
            "employment_type": clean_text(payload["employment_type"], 60),
            "years_experience": clean_text(payload["years_experience"], 40),
            "department_name": department["name"],
        },
        interests=payload.get("interests", []) if isinstance(payload.get("interests"), list) else [],
    )
    request = organizations_repo.create_approval_request(
        {
            "request_type": "MEMBERSHIP",
            "applicant_user_id": user["_id"],
            "organization_id": org["_id"],
            "requested_role": ROLE_EMPLOYEE,
            "assigned_approver_role": ROLE_ORGANIZATION_ADMIN,
        }
    )
    _notify_approvers(request, "New employee registration pending")
    verification = _issue_verification(user)
    return {
        "user": public_user(user),
        "organization": {"_id": org["_id"], "name": org["name"]},
        "department": {"_id": department["_id"], "name": department["name"]},
        "verification": verification,
        "message": (
            "Your registration has been submitted. Verify your email, then your organization "
            "administrator will approve your membership."
        ),
    }


def _mark_user_verified(user: dict) -> dict:
    fields = {
        "email_verified": True,
        "email_verification_token": None,
        "email_verification_expires_at": None,
    }
    if user.get("account_status") == "EMAIL_VERIFICATION_PENDING":
        fields["account_status"] = "PENDING_APPROVAL"
    users_repo.update_user(user["_id"], fields)
    return {
        "already_verified": False,
        "account_status": fields.get("account_status", user.get("account_status")),
    }


def verify_otp(email: str, code: str) -> dict:
    email = normalize_email(email)
    code = clean_text(code, 10)
    if not email or not code.isdigit() or len(code) != 6:
        raise AppError("Enter the 6-digit code from your email.", "INVALID_OTP", 422)
    user = users_repo.find_by_email(email)
    if not user:
        raise AppError("That verification code is invalid or has expired.", "INVALID_OTP", 422)
    if user.get("email_verified"):
        return {"already_verified": True, "account_status": user.get("account_status")}

    record = otp_repo.find_active(email, "EMAIL_VERIFICATION")
    if not record:
        raise AppError("Request a new verification code to continue.", "OTP_NOT_FOUND", 422)
    if _is_expired(record.get("expires_at")):
        otp_repo.consume(record["_id"])
        raise AppError("That verification code has expired. Request a new one.", "OTP_EXPIRED", 422)
    if int(record.get("attempts", 0)) >= int(record.get("max_attempts", 5)):
        otp_repo.consume(record["_id"])
        raise AppError("Too many incorrect attempts. Request a new code.", "OTP_LOCKED", 429)

    if not hmac.compare_digest(record.get("code_hash", ""), _hash_otp(user["_id"], code)):
        attempts = otp_repo.increment_attempt(record["_id"])
        remaining = max(0, int(record.get("max_attempts", 5)) - attempts)
        if remaining == 0:
            otp_repo.consume(record["_id"])
            raise AppError("Too many incorrect attempts. Request a new code.", "OTP_LOCKED", 429)
        raise AppError(
            "That verification code is incorrect.",
            "INVALID_OTP",
            422,
            {"attempts_remaining": remaining},
        )

    otp_repo.consume(record["_id"])
    result = _mark_user_verified(user)
    ops_service.safe_log("email_verified", user_id=user["_id"])
    return result


def resend_otp(email: str) -> dict:
    email = normalize_email(email)
    user = users_repo.find_by_email(email)
    if not user:
        raise AppError("If that account exists, a new code has been sent.", "OTP_SENT", 200)
    if user.get("email_verified"):
        raise AppError("This email address is already verified.", "ALREADY_VERIFIED", 409)

    cooldown = int(current_app.config.get("OTP_RESEND_SECONDS", 60))
    latest = otp_repo.find_latest(email, "EMAIL_VERIFICATION")
    if latest and latest.get("last_sent_at"):
        sent_at = latest["last_sent_at"]
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)
        elapsed = (now_utc() - sent_at).total_seconds()
        if elapsed < cooldown:
            raise AppError(
                "Please wait before requesting another code.",
                "OTP_RESEND_COOLDOWN",
                429,
                {"retry_after_seconds": int(cooldown - elapsed)},
            )
    if otp_repo.count_since(email, now_utc() - timedelta(hours=1), "EMAIL_VERIFICATION") >= 5:
        raise AppError("Too many codes requested. Try again later.", "RATE_LIMITED", 429)

    return _issue_verification(user)


def verify_email(raw_token: str) -> dict:
    if not raw_token:
        raise AppError("This verification link is invalid.", "INVALID_TOKEN", 400)
    user = users_repo.find_by_verification_token(_hash_token(raw_token))
    if not user:
        raise AppError("This verification link is invalid or has already been used.", "INVALID_TOKEN", 400)
    if _is_expired(user.get("email_verification_expires_at")):
        raise AppError("This verification link has expired. Please contact support.", "TOKEN_EXPIRED", 400)
    if user.get("email_verified"):
        return {"already_verified": True, "account_status": user.get("account_status")}
    fields = {
        "email_verified": True,
        "email_verification_token": None,
        "email_verification_expires_at": None,
    }
    if user.get("account_status") == "EMAIL_VERIFICATION_PENDING":
        fields["account_status"] = "PENDING_APPROVAL"
    users_repo.update_user(user["_id"], fields)
    return {
        "already_verified": False,
        "account_status": fields.get("account_status", user.get("account_status")),
    }


def login(email: str, password: str) -> dict:
    user = users_repo.find_by_email(normalize_email(email))
    if not user or not verify_password(password, user.get("password_hash", "")):
        raise AppError("Incorrect email or password.", "INVALID_CREDENTIALS", 401)
    if not user.get("email_verified"):
        raise AppError(
            "Please verify your email address before signing in.",
            "EMAIL_NOT_VERIFIED",
            403,
            {"account_status": user.get("account_status")},
        )
    if user.get("account_status") != "APPROVED":
        messages = {
            "PENDING_APPROVAL": "Your account is waiting for administrator approval.",
            "REJECTED": "Your registration was not approved. Please contact your administrator.",
            "SUSPENDED": "Your account is suspended. Please contact your administrator.",
            "INACTIVE": "Your account is inactive.",
        }
        raise AppError(
            messages.get(user.get("account_status"), "Your account is not active yet."),
            "ACCOUNT_NOT_ACTIVE",
            403,
            {"account_status": user.get("account_status")},
        )
    if user.get("role") != ROLE_SUPER_ADMIN:
        org = organizations_repo.find_org(user.get("organization_id"))
        if not org or org.get("approval_status") != "APPROVED":
            raise AppError(
                "Your organization is not currently active. Please contact support.",
                "ORGANIZATION_INACTIVE",
                403,
            )
    login_user(user["_id"])
    return {"user": public_user(user)}


def logout() -> None:
    logout_user()

