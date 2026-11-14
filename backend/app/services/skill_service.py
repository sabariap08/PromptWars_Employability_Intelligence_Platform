"""Skill evidence aggregation and proficiency recomputation."""
from app.repositories import catalog_repo, profiles_repo
from app.services import scoring
from app.utils.ids import now_utc


def _ensure_skill_catalog(name: str) -> dict:
    existing = catalog_repo.find_skill_by_name(name)
    return existing or catalog_repo.upsert_skill(name)


def add_self_skill(user_id: str, org_id: str, skill_name: str, level: str) -> dict:
    skill_name = (skill_name or "").strip()
    level = (level or "BEGINNER").upper()
    if level not in scoring.SELF_LEVEL_SCORE:
        level = "BEGINNER"
    _ensure_skill_catalog(skill_name)
    profiles_repo.upsert_learner_skill(
        user_id, org_id, skill_name, {"self_level": level, "skill_id": catalog_repo.find_skill_by_name(skill_name)["_id"]}
    )
    already_declared = any(
        item.get("source_type") == "SELF_DECLARED"
        for item in profiles_repo.list_evidence(user_id, skill_name)
    )
    if not already_declared:
        profiles_repo.add_evidence(
            {
                "user_id": user_id,
                "organization_id": org_id,
                "skill_name": skill_name,
                "source_type": "SELF_DECLARED",
                "title": "Self-declared skill level",
                "score": scoring.SELF_LEVEL_SCORE[level],
                "verified": False,
            }
        )
    return recompute_skill(user_id, org_id, skill_name)


def remove_self_skill(user_id: str, skill_name: str) -> None:
    profiles_repo.delete_learner_skill(user_id, skill_name)


def add_evidence(user_id: str, org_id: str, skill_name: str, source_type: str, score: float, title: str = "", source_id: str | None = None, verified: bool = False) -> dict:
    _ensure_skill_catalog(skill_name)
    profiles_repo.add_evidence(
        {
            "user_id": user_id,
            "organization_id": org_id,
            "skill_name": skill_name,
            "source_type": source_type,
            "source_id": source_id,
            "title": title,
            "score": score,
            "verified": verified,
        }
    )
    return recompute_skill(user_id, org_id, skill_name)


def recompute_skill(user_id: str, org_id: str, skill_name: str) -> dict:
    learner_skill = profiles_repo.find_learner_skill(user_id, skill_name)
    evidence = profiles_repo.list_evidence(user_id, skill_name)
    self_level = learner_skill.get("self_level") if learner_skill else None
    result = scoring.calculate_proficiency(evidence, self_level)

    existing = learner_skill or profiles_repo.upsert_learner_skill(
        user_id, org_id, skill_name, {"skill_id": (catalog_repo.find_skill_by_name(skill_name) or {}).get("_id")}
    )
    history = existing.get("history", [])
    history.append(
        {
            "proficiency": result["proficiency"],
            "confidence": result["confidence"],
            "at": now_utc(),
        }
    )
    existing.update(
        {
            "proficiency": result["proficiency"],
            "confidence": result["confidence"],
            "verification_status": result["verification_status"],
            "evidence_count": result["evidence_count"],
            "breakdown": result["breakdown"],
            "history": history[-40:],
            "last_assessed_at": max(
                [e.get("created_at") for e in evidence if e.get("source_type") == "ASSESSMENT"],
                default=existing.get("last_assessed_at"),
            ),
            "updated_at": now_utc(),
        }
    )
    profiles_repo.save_learner_skill(existing)
    return existing


def recompute_all(user_id: str, org_id: str) -> list:
    results = []
    for learner_skill in profiles_repo.list_learner_skills(user_id):
        results.append(recompute_skill(user_id, org_id, learner_skill["skill_name"]))
    return results


def skill_profile(user_id: str) -> list:
    return profiles_repo.list_learner_skills(user_id)


def evidence_for(user_id: str, skill_name: str | None = None) -> list:
    return profiles_repo.list_evidence(user_id, skill_name)
