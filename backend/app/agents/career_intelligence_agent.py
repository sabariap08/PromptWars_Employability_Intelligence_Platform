"""Agent 4 - Career Intelligence: explainable readiness and alternatives."""
from app.agents.base import BaseAgent
from app.services import career_service


class CareerIntelligenceAgent(BaseAgent):
    name = "career_intelligence"
    label = "Career Intelligence Agent"

    def run(self, state: dict) -> dict:
        user = state["user"]
        analysis = career_service.analyze(user["_id"])
        if not analysis:
            return {"has_target": False, "_provider": "deterministic", "_model": "rules"}
        alternatives = career_service.alternative_careers(user["_id"], analysis["career_id"])
        fallback = (
            f"You are {analysis['readiness']}% ready for {analysis['career_name']}. "
            f"You already demonstrate {len(analysis['strengths'])} of the required skills. "
            + (
                f"The biggest opportunity is {analysis['gaps'][0]['skill_name']}."
                if analysis["gaps"]
                else "Your profile covers the core requirements."
            )
        )
        response = self.ai_text(
            "Write two encouraging sentences for a learner. Facts: "
            f"career={analysis['career_name']}, readiness={analysis['readiness']}%, "
            f"strong_skills={[s['skill_name'] for s in analysis['strengths'][:4]]}, "
            f"top_gaps={[g['skill_name'] for g in analysis['gaps'][:3]]}. "
            "Do not invent numbers or skills. Keep it under 60 words.",
            system="You explain career readiness using only the supplied facts.",
            fallback=fallback,
        )
        return {
            "has_target": True,
            "career_name": analysis["career_name"],
            "readiness": analysis["readiness"],
            "gaps": analysis["gaps"][:6],
            "strengths": [item["skill_name"] for item in analysis["strengths"][:6]],
            "alternatives": alternatives,
            "explanation": response["text"],
            "_provider": response["provider"],
            "_model": response["model"],
            "_ai": response["_ai"],
        }
