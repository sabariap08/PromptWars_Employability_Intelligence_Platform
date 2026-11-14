"""Agent 5 - Learning Recommendation: builds and adapts the roadmap."""
from app.agents.base import BaseAgent
from app.repositories import learning_repo, profiles_repo
from app.services import learning_service


class LearningRecommendationAgent(BaseAgent):
    name = "learning_recommendation"
    label = "Learning Recommendation Agent"

    def run(self, state: dict) -> dict:
        user = state["user"]
        event = state["event"]
        profile = profiles_repo.find_profile(user["_id"]) or {}
        if not profile.get("target_career_id"):
            return {"skipped": True, "reason": "No target career selected.", "_provider": "deterministic", "_model": "rules"}

        roadmap = learning_repo.active_roadmap(user["_id"])
        progress = state.get("results", {}).get("progress_evaluation", {})
        latest_score = progress.get("latest_score")
        primary_skill = progress.get("primary_skill")
        weak_skills = progress.get("weak_skills", [])

        if event == "career.changed" or not roadmap:
            roadmap = learning_service.generate_roadmap(
                user,
                trigger="career_change" if event == "career.changed" else "initial",
            )
            message = (
                f"A new roadmap was generated for {roadmap['career_name']} with "
                f"{len(roadmap['phases'])} phase(s). Completed history was preserved."
            )
        elif event == "assessment.submitted" and latest_score is not None:
            adaptation = learning_service.adapt_after_assessment(
                user, primary_skill or (weak_skills[0] if weak_skills else "the assessed skill"), latest_score, weak_skills
            )
            roadmap = adaptation["roadmap"] if adaptation else roadmap
            message = adaptation["message"] if adaptation else "No roadmap change was required."
        else:
            message = "Existing roadmap kept. No structural change required for this event."

        summary = learning_service.roadmap_summary(roadmap)
        return {
            "career_name": summary.get("career_name"),
            "version": summary.get("version"),
            "completion": summary.get("completion"),
            "next_tasks": [
                {"title": task["resource_title"], "skill": task["skill_name"], "hours": task["est_hours"]}
                for task in summary.get("next_tasks", [])
            ],
            "message": message,
            "_provider": "deterministic",
            "_model": "rules",
        }
