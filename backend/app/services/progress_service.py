"""Aggregate learner progress and dashboard data."""
from app.repositories import (
    assessments_repo,
    learning_repo,
    operations_repo,
    profiles_repo,
)
from app.services import career_service, learning_service, profile_service


def compute(user: dict) -> dict:
    analysis = career_service.analyze(user["_id"]) or {}
    roadmap = learning_repo.active_roadmap(user["_id"])
    summary = learning_service.roadmap_summary(roadmap)
    attempts = [a for a in assessments_repo.list_attempts(user["_id"]) if a["status"] == "EVALUATED"]
    scores = [a["score"] for a in attempts if a.get("score") is not None]
    skills = profiles_repo.list_learner_skills(user["_id"])
    verified = sum(1 for skill in skills if skill.get("verification_status") == "VERIFIED")

    progress = learning_repo.upsert_progress(
        user["_id"],
        {
            "organization_id": user.get("organization_id"),
            "career_readiness": analysis.get("readiness", 0),
            "roadmap_completion": summary.get("completion", 0),
            "skills_verified": verified,
            "assessments_taken": len(attempts),
            "average_score": round(sum(scores) / len(scores)) if scores else 0,
            "last_activity_at": (learning_repo.list_activity(user["_id"], 1) or [{}])[0].get("created_at"),
        },
    )
    progress["next_tasks"] = summary.get("next_tasks", [])
    progress["roadmap"] = summary
    progress["career"] = analysis
    return progress


def dashboard(user: dict) -> dict:
    progress = compute(user)
    profile = profiles_repo.find_profile(user["_id"])
    skills = profiles_repo.list_learner_skills(user["_id"])
    completeness = profile_service.profile_completeness(user, profile, len(skills))
    notifications = operations_repo.list_notifications(user["_id"], 8)
    recent_attempts = assessments_repo.list_attempts(user["_id"])[:5]
    roadmap = learning_repo.active_roadmap(user["_id"])

    return {
        "dashboard": {
            "profile_completion": completeness,
            "skills_total": len(skills),
            "skills_verified": progress.get("skills_verified", 0),
            "career_readiness": progress.get("career_readiness", 0),
            "roadmap_completion": progress.get("roadmap_completion", 0),
            "assessments_taken": progress.get("assessments_taken", 0),
            "average_score": progress.get("average_score", 0),
            "strengths": (progress.get("career") or {}).get("strengths", [])[:4],
            "gaps": (progress.get("career") or {}).get("gaps", [])[:5],
            "career_name": (progress.get("career") or {}).get("career_name", ""),
            "next_tasks": progress.get("next_tasks", []),
            "roadmap": progress.get("roadmap", {}),
            "recent_attempts": [
                {
                    "_id": a["_id"],
                    "title": a.get("title"),
                    "purpose": a.get("purpose"),
                    "score": a.get("score"),
                    "status": a["status"],
                    "evaluated_at": a.get("evaluated_at"),
                }
                for a in recent_attempts
            ],
            "notifications": notifications,
            "unread_notifications": operations_repo.unread_count(user["_id"]),
            "onboarding_complete": bool(profile and profile.get("onboarding_complete")),
            "has_target_career": bool(profile and profile.get("target_career_id")),
            "roadmap_id": roadmap["_id"] if roadmap else None,
        }
    }
