"""Agent 3 - Skill Analysis: aggregates evidence into explainable proficiency."""
from app.agents.base import BaseAgent
from app.services import career_service, skill_service


class SkillAnalysisAgent(BaseAgent):
    name = "skill_analysis"
    label = "Skill Analysis Agent"

    def run(self, state: dict) -> dict:
        user = state["user"]
        skills = skill_service.recompute_all(user["_id"], user.get("organization_id"))
        weak = [skill["skill_name"] for skill in skills if skill.get("proficiency", 0) < 40]
        strong = [skill["skill_name"] for skill in skills if skill.get("proficiency", 0) >= 60]
        verified = [skill["skill_name"] for skill in skills if skill.get("verification_status") == "VERIFIED"]
        analysis = career_service.analyze(user["_id"]) or {}
        return {
            "skill_count": len(skills),
            "verified_count": len(verified),
            "strong_skills": strong[:6],
            "weak_skills": weak[:6],
            "missing_skills": [gap["skill_name"] for gap in analysis.get("gaps", []) if gap["status"] == "MISSING"][:6],
            "evidence_total": sum(skill.get("evidence_count", 0) for skill in skills),
            "_provider": "deterministic",
            "_model": "rules",
        }
