"""Index creation for all EIP collections (idempotent)."""

import logging

logger = logging.getLogger(__name__)


def ensure_indexes(db) -> None:
    def idx(collection, keys, **kwargs):
        try:
            db[collection].create_index(keys, **kwargs)
        except Exception as exc:  # noqa: BLE001 - indexing must never block startup
            # Indexes are an optimization; mongomock or restricted Atlas users
            # may not support every option. Indexing failures must not break startup.
            logger.debug("Skipped index on %s: %s", collection, exc)

    idx("users", "email", unique=True)
    idx("users", [("organization_id", 1), ("role", 1), ("account_status", 1)])
    idx("users", "email_verification_token")
    idx("otp_records", [("email", 1), ("purpose", 1), ("consumed", 1)])
    idx("otp_records", [("user_id", 1), ("purpose", 1)])
    idx("affiliation_requests", [("current_organization_id", 1), ("status", 1)])
    idx("affiliation_requests", [("requested_organization_id", 1), ("status", 1)])
    idx("affiliation_requests", [("user_id", 1), ("status", 1)])
    idx("organizations", "name")
    idx("organizations", [("organization_type", 1), ("approval_status", 1)])
    idx("organizations", "official_email")
    idx("organizations", "registration_identifier")
    idx("departments", [("organization_id", 1), ("name", 1)])
    idx("learner_profiles", "user_id", unique=True)
    idx("learner_profiles", "organization_id")
    idx("skills", "name", unique=True)
    idx("learner_skills", [("user_id", 1), ("skill_name", 1)], unique=True)
    idx("learner_skills", [("organization_id", 1), ("skill_name", 1)])
    idx("skill_evidence", [("user_id", 1), ("skill_name", 1)])
    idx("certifications", "user_id")
    idx("projects", "user_id")
    idx("career_roles", "name")
    idx("assessment_questions", [("skill_name", 1), ("difficulty", 1)])
    idx("assessments", "user_id")
    idx("assessment_attempts", [("user_id", 1), ("status", 1)])
    idx("assessment_attempts", "assessment_id")
    idx("assessment_integrity_events", "attempt_id")
    idx("learning_resources", "skill_names")
    idx("courses", [("is_active", 1), ("difficulty", 1)])
    idx("courses", "skill_names")
    idx("course_enrollments", [("user_id", 1), ("course_id", 1)], unique=True)
    idx("course_enrollments", [("user_id", 1), ("status", 1)])
    idx("course_enrollments", "organization_id")
    idx("learning_roadmaps", [("user_id", 1), ("status", 1)])
    idx("learning_activity", [("user_id", 1), ("created_at", -1)])
    idx("progress_records", "user_id", unique=True)
    idx("mentor_conversations", "user_id", unique=True)
    idx("trainer_assignments", [("trainer_id", 1), ("learner_id", 1)])
    idx("trainer_feedback", "learner_id")
    idx("ai_agent_executions", "created_at")
    idx("notifications", [("user_id", 1), ("read", 1)])
    idx("audit_logs", "created_at")
    idx("approval_requests", [("organization_id", 1), ("status", 1)])
    idx("approval_requests", "applicant_user_id")
