"""Agent 2 - Assessment and Integrity: prepares and evaluates assessments."""
from app.agents.base import BaseAgent
from app.repositories import assessments_repo, profiles_repo
from app.services import assessment_service, skill_service


class AssessmentAgent(BaseAgent):
    name = "assessment"
    label = "Assessment & Integrity Agent"

    def run(self, state: dict) -> dict:
        user = state["user"]
        event = state["event"]
        payload = state.get("payload", {})

        if event == "profile.completed":
            existing = [
                item
                for item in assessments_repo.list_assessments(user["_id"])
                if item.get("purpose") == "BASELINE"
            ]
            if existing:
                return {
                    "assessment_id": existing[-1]["_id"],
                    "created": False,
                    "message": "Baseline assessment already prepared.",
                    "_provider": "deterministic",
                    "_model": "rules",
                }
            assessment = assessment_service.create_baseline(user)
            return {
                "assessment_id": assessment["_id"],
                "created": True,
                "question_count_hint": len(assessment.get("question_ids", [])),
                "message": "Baseline assessment prepared from the learner's skills and target career.",
                "_provider": "deterministic",
                "_model": "rules",
            }

        if event == "assessment.submitted":
            attempt_id = payload.get("attempt_id", "")
            attempt = assessments_repo.find_attempt(attempt_id, user["_id"])
            if not attempt:
                raise ValueError("Assessment attempt not found for evaluation.")
            if attempt["status"] == "SUBMITTED":
                attempt = assessment_service.evaluate_attempt(attempt_id)
            skill_service.recompute_all(user["_id"], user.get("organization_id"))
            weak = {skill: score for skill, score in (attempt.get("topic_scores") or {}).items() if score < 50}
            return {
                "attempt_id": attempt_id,
                "score": attempt.get("score"),
                "topic_scores": attempt.get("topic_scores", {}),
                "weak_skills": list(weak.keys()),
                "integrity_risk": (attempt.get("integrity") or {}).get("risk_level", "LOW"),
                "integrity_flags": (attempt.get("integrity") or {}).get("flags", []),
                "summary": attempt.get("summary", ""),
                "_provider": "deterministic",
                "_model": "rules",
            }

        if event == "certification.added":
            cert = profiles_repo.find_certification(payload.get("certification_id", ""), user["_id"])
            if not cert:
                raise ValueError("Certification not found.")
            if cert.get("assessment_id"):
                return {
                    "assessment_id": cert["assessment_id"],
                    "created": False,
                    "message": "Verification check already exists.",
                    "_provider": "deterministic",
                    "_model": "rules",
                }
            assessment = assessment_service.create_certification_check(user, cert)
            profiles_repo.update_certification(cert["_id"], {"assessment_id": assessment["_id"]})
            return {
                "assessment_id": assessment["_id"],
                "created": True,
                "certification_id": cert["_id"],
                "message": "Certification verification check created. Evidence stays pending until it is passed.",
                "_provider": "deterministic",
                "_model": "rules",
            }

        if event == "project.added":
            project = profiles_repo.find_project(payload.get("project_id", ""), user["_id"])
            if not project:
                raise ValueError("Project not found.")
            if (project.get("ai_analysis") or {}).get("follow_up_assessment_id"):
                return {
                    "assessment_id": project["ai_analysis"]["follow_up_assessment_id"],
                    "created": False,
                    "_provider": "deterministic",
                    "_model": "rules",
                }
            assessment = assessment_service.create_project_check(user, project)
            analysis = dict(project.get("ai_analysis") or {})
            analysis["follow_up_assessment_id"] = assessment["_id"]
            profiles_repo.update_project(project["_id"], {"ai_analysis": analysis})
            return {
                "assessment_id": assessment["_id"],
                "created": True,
                "message": "Project follow-up assessment prepared for practical evidence.",
                "_provider": "deterministic",
                "_model": "rules",
            }

        return {"skipped": True, "reason": f"No assessment action for event {event}."}
