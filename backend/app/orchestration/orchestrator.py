"""Central agent orchestrator: conditional routing, handoffs and execution history."""
import json
import logging
import time

from app.agents.ai_mentor_agent import AIMentorAgent
from app.agents.assessment_agent import AssessmentAgent
from app.agents.career_intelligence_agent import CareerIntelligenceAgent
from app.agents.learning_recommendation_agent import LearningRecommendationAgent
from app.agents.profile_agent import ProfileAgent
from app.agents.progress_evaluation_agent import ProgressEvaluationAgent
from app.agents.skill_analysis_agent import SkillAnalysisAgent
from app.orchestration.workflow_registry import WORKFLOWS
from app.repositories import operations_repo
from app.utils.text import truncate

logger = logging.getLogger("eip.agents")

AGENTS = {
    "profile": ProfileAgent,
    "assessment": AssessmentAgent,
    "skill_analysis": SkillAnalysisAgent,
    "career_intelligence": CareerIntelligenceAgent,
    "learning_recommendation": LearningRecommendationAgent,
    "progress_evaluation": ProgressEvaluationAgent,
    "ai_mentor": AIMentorAgent,
}

SUMMARY_EXCLUDED_KEYS = {"_provider", "_model", "_ai", "explanation", "message"}


def _summarize(output: dict) -> str:
    safe = {key: value for key, value in output.items() if key not in SUMMARY_EXCLUDED_KEYS}
    try:
        text = json.dumps(safe, default=str)
    except (TypeError, ValueError):
        text = str(safe)
    return truncate(text, 300)


def run_workflow(event: str, user: dict, payload: dict | None = None) -> dict:
    """Run the workflow registered for an event. Unknown events are a no-op."""
    names = WORKFLOWS.get(event)
    if not names:
        return {"workflow": event, "executions": [], "results": {}, "skipped": True}

    payload = payload or {}
    state = {"event": event, "user": user, "payload": payload, "results": {}}
    executions = []

    for index, name in enumerate(names):
        agent_class = AGENTS.get(name)
        if not agent_class:
            continue
        agent = agent_class()
        handoff_to = names[index + 1] if index + 1 < len(names) else ""
        started = time.perf_counter()
        status = "SUCCESS"
        output = {}
        error = ""
        try:
            output = agent.run(state) or {}
        except Exception as exc:  # one agent failure must not cancel the workflow
            status = "FAILED"
            error = str(exc)[:300]
            logger.exception("Agent %s failed during %s", agent.name, event)
        duration_ms = int((time.perf_counter() - started) * 1000)
        state["results"][name] = output

        provider = output.get("_provider", "deterministic")
        model = output.get("_model", "rules")
        operations_repo.record_execution(
            {
                "workflow": event,
                "agent_name": agent.name,
                "event": event,
                "status": status,
                "provider": provider,
                "model": model,
                "user_id": user["_id"],
                "organization_id": user.get("organization_id"),
                "input_summary": f"{event} · role={user.get('role')}",
                "output_summary": _summarize(output) if output else "",
                "duration_ms": duration_ms,
                "error": error,
                "handoff_to": handoff_to,
            }
        )
        executions.append(
            {
                "agent": agent.name,
                "label": agent.label,
                "status": status,
                "provider": provider,
                "model": model,
                "duration_ms": duration_ms,
                "handoff_to": handoff_to,
                "summary": _summarize(output) if output else "",
                "error": error,
            }
        )

    return {"workflow": event, "executions": executions, "results": state["results"], "skipped": False}
