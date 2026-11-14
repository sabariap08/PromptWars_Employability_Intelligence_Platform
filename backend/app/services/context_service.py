"""Minimal, privacy-conscious learner context for AI prompts and mentor replies."""
from app.repositories import assessments_repo, learning_repo, profiles_repo
from app.services import career_service, learning_service


def build(user: dict) -> dict:
    profile = profiles_repo.find_profile(user["_id"]) or {}
    analysis = career_service.analyze(user["_id"]) or {}
    roadmap = learning_repo.active_roadmap(user["_id"])
    summary = learning_service.roadmap_summary(roadmap)
    latest = assessments_repo.latest_evaluated_attempt(user["_id"])
    skills = profiles_repo.list_learner_skills(user["_id"])

    first_name = (user.get("full_name") or "there").split()[0]
    return {
        "first_name": first_name,
        "learner_type": "student" if user.get("role") == "STUDENT" else "employee",
        "career_name": analysis.get("career_name", ""),
        "readiness": analysis.get("readiness", 0),
        "top_gaps": [
            {"skill": gap["skill_name"], "current": gap["current"], "required": gap["required"]}
            for gap in analysis.get("gaps", [])[:3]
        ],
        "strengths": [item["skill_name"] for item in analysis.get("strengths", [])[:3]],
        "next_tasks": [
            {"title": task["resource_title"], "skill": task["skill_name"], "hours": task["est_hours"]}
            for task in summary.get("next_tasks", [])[:3]
        ],
        "latest_score": latest.get("score") if latest else None,
        "latest_assessment": latest.get("title") if latest else "",
        "roadmap_version": summary.get("version") if summary.get("has_roadmap") else None,
        "plan_trigger": summary.get("trigger"),
        "plan_rationale": summary.get("rationale"),
        "verified_skills": sum(1 for s in skills if s.get("verification_status") == "VERIFIED"),
        "total_skills": len(skills),
        "weekly_hours": profile.get("weekly_hours", 6),
    }
