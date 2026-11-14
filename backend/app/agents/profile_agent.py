"""Agent 1 - Profile Intelligence: structures learner context and evidence."""
from app.agents.base import BaseAgent
from app.repositories import catalog_repo, profiles_repo


class ProfileAgent(BaseAgent):
    name = "profile"
    label = "Profile Intelligence Agent"

    def run(self, state: dict) -> dict:
        user = state["user"]
        profile = profiles_repo.find_profile(user["_id"]) or profiles_repo.create_profile(
            user["_id"], user.get("organization_id"), user.get("role", "STUDENT")
        )
        skills = profiles_repo.list_learner_skills(user["_id"])
        certs = profiles_repo.list_certifications(user["_id"])
        projects = profiles_repo.list_projects(user["_id"])
        career = catalog_repo.find_career(profile.get("target_career_id")) if profile.get("target_career_id") else None

        missing = []
        if not career:
            missing.append("target_career_id")
        if not skills:
            missing.append("skills")
        if not profile.get("learning_style"):
            missing.append("learning_style")
        if not profile.get("weekly_hours"):
            missing.append("weekly_hours")

        if state["event"] == "project.added":
            project = profiles_repo.find_project(state["payload"].get("project_id", ""), user["_id"])
            if project:
                existing = {
                    item.get("source_id")
                    for item in profiles_repo.list_evidence(user["_id"])
                    if item.get("source_type") == "PROJECT"
                }
                if project["_id"] not in existing:
                    from app.services import skill_service

                    for skill in project.get("skills", [])[:10]:
                        skill_service.add_evidence(
                            user["_id"],
                            user.get("organization_id"),
                            skill,
                            "PROJECT",
                            55,
                            title=project["name"],
                            source_id=project["_id"],
                            verified=False,
                        )
                profiles_repo.update_project(
                    project["_id"],
                    {
                        "ai_analysis": {
                            "skills_detected": project.get("skills", []),
                            "technologies": project.get("technologies", []),
                            "summary": (
                                f"{len(project.get('skills', []))} skill signals detected from the project "
                                "description. Evidence is pending verification."
                            ),
                            "needs_verification": project.get("status") != "VERIFIED",
                        }
                    },
                )

        return {
            "profile_summary": {
                "learner_type": profile.get("learner_type"),
                "target_career": career["name"] if career else "",
                "skills": len(skills),
                "certifications": len(certs),
                "projects": len(projects),
                "onboarding_complete": bool(profile.get("onboarding_complete")),
            },
            "missing_fields": missing,
            "_provider": "deterministic",
            "_model": "rules",
        }
