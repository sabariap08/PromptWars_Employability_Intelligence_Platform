"""Explainable career matching and readiness calculation."""
from app.repositories import catalog_repo, profiles_repo
from app.utils.responses import AppError


def _learner_skill_map(user_id: str) -> dict:
    return {skill["skill_name"]: skill for skill in profiles_repo.list_learner_skills(user_id)}


def _attainment(proficiency: float, required: float) -> float:
    if required <= 0:
        return 1.0
    return max(0.0, min(1.0, proficiency / required))


def analyze_role(user_id: str, role: dict) -> dict:
    return analyze_with_skills(_learner_skill_map(user_id), role)


def analyze_with_skills(skills: dict, role: dict) -> dict:
    requirements = role.get("required_skills", [])
    total_weight = 0.0
    weighted = 0.0
    gaps = []
    strengths = []
    skill_rows = []

    for requirement in requirements:
        name = requirement.get("skill_name", "")
        required = float(requirement.get("min_proficiency", 60))
        weight = float(requirement.get("weight", max(1.0, required / 30)))
        learner_skill = skills.get(name)
        current = float(learner_skill.get("proficiency", 0)) if learner_skill else 0.0
        verified = learner_skill.get("verification_status") == "VERIFIED" if learner_skill else False
        attained = _attainment(current, required)
        total_weight += weight
        weighted += weight * attained

        if current <= 0:
            status = "MISSING"
        elif current < required:
            status = "WEAK"
        else:
            status = "STRONG"

        row = {
            "skill_name": name,
            "current": round(current),
            "required": round(required),
            "status": status,
            "verified": verified,
            "attainment": round(attained * 100),
            "weight": weight,
        }
        skill_rows.append(row)
        if status == "STRONG":
            strengths.append(row)
        else:
            deficit = required - current
            gaps.append({**row, "priority": round(weight * deficit / 100, 2)})

    gaps.sort(key=lambda g: (0 if g["status"] == "MISSING" else 1, -g["priority"]))
    readiness = round(weighted / total_weight * 100) if total_weight else 0

    return {
        "career_id": role["_id"],
        "career_name": role["name"],
        "readiness": readiness,
        "gaps": gaps,
        "strengths": strengths,
        "skills": skill_rows,
        "required_count": len(requirements),
        "strong_count": len(strengths),
        "preferred_skills": role.get("preferred_skills", []),
    }


def analyze(user_id: str, role: dict | None = None) -> dict | None:
    if role is None:
        profile = profiles_repo.find_profile(user_id)
        if not profile or not profile.get("target_career_id"):
            return None
        role = catalog_repo.find_career(profile["target_career_id"])
    if not role:
        return None
    return analyze_role(user_id, role)


def alternative_careers(user_id: str, exclude_id: str, limit: int = 3) -> list:
    alternatives = []
    for role in catalog_repo.list_careers():
        if role["_id"] == exclude_id:
            continue
        analysis = analyze_role(user_id, role)
        alternatives.append(
            {
                "career_id": role["_id"],
                "career_name": role["name"],
                "readiness": analysis["readiness"],
                "top_gap": analysis["gaps"][0]["skill_name"] if analysis["gaps"] else "",
            }
        )
    alternatives.sort(key=lambda item: -item["readiness"])
    return alternatives[:limit]


def set_target_career(user_id: str, career_id: str) -> dict:
    role = catalog_repo.find_career(career_id)
    if not role or not role.get("is_active"):
        raise AppError("That career path is not available.", "CAREER_NOT_FOUND", 404)
    profiles_repo.update_profile(user_id, {"target_career_id": career_id})
    return role


def readiness_summary(user_id: str) -> dict:
    analysis = analyze(user_id)
    if not analysis:
        return {
            "career_name": "",
            "readiness": 0,
            "gaps": [],
            "strengths": [],
            "has_target": False,
        }
    return {**analysis, "has_target": True}
