"""Agent 7 - AI Mentor: turns pipeline results into friendly, actionable guidance."""
from app.agents.base import BaseAgent
from app.services import context_service, mentor_service, ops_service


class AIMentorAgent(BaseAgent):
    name = "ai_mentor"
    label = "AI Mentor Agent"

    def run(self, state: dict) -> dict:
        user = state["user"]
        event = state["event"]
        context = context_service.build(user)
        details = {}
        results = state.get("results", {})

        if event == "assessment.submitted":
            assessment = results.get("assessment", {})
            details = {
                "score": assessment.get("score"),
                "assessment_title": state.get("payload", {}).get("assessment_title", "your assessment"),
                "weak_skills": assessment.get("weak_skills", []),
            }
        elif event == "career.changed":
            details = {"career_name": results.get("career_intelligence", {}).get("career_name", "")}
        elif event == "trainer.feedback":
            details = {"skill_name": state.get("payload", {}).get("skill_name", "")}

        fallback = mentor_service.explain_change(context, event, details)
        prompt = (
            "Write a short, friendly update for a learner about this event. Facts: "
            f"event={event}, details={details}, readiness={context.get('readiness')}, "
            f"career={context.get('career_name')}, next_tasks={context.get('next_tasks')}. "
            "Do not invent scores, courses or skills. Maximum 90 words."
        )
        response = self.ai_text(
            prompt,
            system="You are a supportive learning mentor. Use only supplied facts.",
            fallback=fallback,
        )
        ops_service.notify(
            user["_id"],
            user.get("organization_id"),
            "Your learning plan update",
            response["text"],
            "LEARNING",
            "/app/roadmap",
        )
        return {
            "message": response["text"],
            "notified": True,
            "_provider": response["provider"],
            "_model": response["model"],
            "_ai": response["_ai"],
        }
