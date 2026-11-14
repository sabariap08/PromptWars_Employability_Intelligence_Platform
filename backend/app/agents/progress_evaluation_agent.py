"""Agent 6 - Progress Evaluation: monitors performance and triggers adaptation signals."""
from app.agents.base import BaseAgent
from app.repositories import assessments_repo, learning_repo
from app.services import progress_service


class ProgressEvaluationAgent(BaseAgent):
    name = "progress_evaluation"
    label = "Progress Evaluation Agent"

    def run(self, state: dict) -> dict:
        user = state["user"]
        progress = progress_service.compute(user)
        latest = assessments_repo.latest_evaluated_attempt(user["_id"])

        weak_skills = []
        primary_skill = ""
        latest_score = None
        if latest:
            latest_score = latest.get("score")
            topic_scores = latest.get("topic_scores") or {}
            weak_skills = [skill for skill, score in topic_scores.items() if score < 50]
            if topic_scores:
                primary_skill = min(topic_scores, key=lambda skill: topic_scores[skill])
                if not weak_skills and latest_score is not None and latest_score < 75:
                    primary_skill = primary_skill

        adaptation = "none"
        if latest_score is not None:
            if latest_score < 50:
                adaptation = "remediation"
            elif latest_score >= 75:
                adaptation = "advance"

        roadmap = learning_repo.active_roadmap(user["_id"])
        tasks = [task for phase in (roadmap or {}).get("phases", []) for task in phase.get("tasks", [])]
        stalled = bool(tasks) and all(task.get("status") == "PENDING" for task in tasks)

        return {
            "career_readiness": progress.get("career_readiness", 0),
            "roadmap_completion": progress.get("roadmap_completion", 0),
            "assessments_taken": progress.get("assessments_taken", 0),
            "average_score": progress.get("average_score", 0),
            "latest_score": latest_score,
            "latest_assessment": latest.get("title") if latest else "",
            "weak_skills": weak_skills,
            "primary_skill": primary_skill,
            "adaptation": adaptation,
            "stalled_plan": stalled,
            "_provider": "deterministic",
            "_model": "rules",
        }
