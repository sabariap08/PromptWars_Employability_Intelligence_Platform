"""Deterministic, explainable scoring. No LLM is involved in these numbers."""

SELF_LEVEL_SCORE = {
    "BEGINNER": 30,
    "INTERMEDIATE": 50,
    "ADVANCED": 75,
    "EXPERT": 90,
}

SOURCE_LABELS = {
    "SELF_DECLARED": "Self-declared level",
    "ASSESSMENT": "Assessment result",
    "CERTIFICATION": "Certification check",
    "PROJECT": "Project evidence",
    "TRAINER": "Trainer verification",
}


def source_weight(source_type: str, verified: bool) -> float:
    if source_type == "ASSESSMENT":
        return 0.45
    if source_type == "TRAINER":
        return 0.35
    if source_type == "CERTIFICATION":
        return 0.25 if verified else 0.12
    if source_type == "PROJECT":
        return 0.25 if verified else 0.12
    if source_type == "SELF_DECLARED":
        return 0.15
    return 0.1


def calculate_proficiency(evidence: list, self_level: str | None = None) -> dict:
    """Weighted, deterministic proficiency plus a transparent breakdown."""
    components = []
    total_weight = 0.0
    weighted_sum = 0.0

    for item in evidence or []:
        source = item.get("source_type", "SELF_DECLARED")
        verified = bool(item.get("verified"))
        score = max(0.0, min(100.0, float(item.get("score", 0))))
        weight = source_weight(source, verified)
        weighted_sum += weight * score
        total_weight += weight
        components.append(
            {
                "source": source,
                "label": SOURCE_LABELS.get(source, source),
                "score": round(score, 1),
                "weight": weight,
                "verified": verified,
                "title": item.get("title", ""),
            }
        )

    level = (self_level or "").upper()
    if level in SELF_LEVEL_SCORE and not any(c["source"] == "SELF_DECLARED" for c in components):
        score = SELF_LEVEL_SCORE[level]
        weight = source_weight("SELF_DECLARED", False)
        weighted_sum += weight * score
        total_weight += weight
        components.append(
            {
                "source": "SELF_DECLARED",
                "label": SOURCE_LABELS["SELF_DECLARED"],
                "score": score,
                "weight": weight,
                "verified": False,
                "title": "Profile self-assessment",
            }
        )

    proficiency = round(weighted_sum / total_weight) if total_weight > 0 else 0
    has_assessment = any(c["source"] in {"ASSESSMENT", "TRAINER"} for c in components)
    has_verified = any(c["verified"] for c in components) or any(
        c["source"] == "ASSESSMENT" and c["score"] >= 60 for c in components
    )

    if total_weight >= 0.8 and has_assessment:
        confidence = "HIGH"
    elif total_weight >= 0.4:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    if has_verified:
        verification = "VERIFIED"
    elif components:
        verification = "PARTIAL"
    else:
        verification = "SELF_REPORTED"

    return {
        "proficiency": proficiency,
        "confidence": confidence,
        "verification_status": verification,
        "breakdown": components,
        "evidence_count": len(evidence or []),
    }


def level_for_score(score: int) -> str:
    if score >= 80:
        return "ADVANCED"
    if score >= 55:
        return "INTERMEDIATE"
    if score >= 25:
        return "BEGINNER"
    return "NOT_STARTED"


def difficulty_for_proficiency(proficiency: int) -> str:
    if proficiency < 30:
        return "BEGINNER"
    if proficiency < 65:
        return "INTERMEDIATE"
    return "ADVANCED"
