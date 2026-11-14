"""Assessment generation, server-side scoring and integrity flagging."""
import random
from datetime import timedelta

from app.repositories import assessments_repo, catalog_repo, profiles_repo
from app.services import ops_service, question_generation_service, skill_service
from app.utils.ids import now_utc
from app.utils.responses import AppError
from app.utils.text import clean_text

MAX_QUESTIONS = question_generation_service.QUESTION_COUNT
OPTION_KEYS = ["A", "B", "C", "D", "E", "F"]
PURPOSE_LABELS = {
    "BASELINE": "Baseline skills assessment",
    "SKILL_CHECK": "Skill check",
    "CERTIFICATION": "Certification verification",
    "PROJECT": "Project follow-up assessment",
}


def _rng():
    return random.Random()


def _seconds_between(start, end):
    if not start or not end:
        return None
    try:
        return (end - start).total_seconds()
    except TypeError:
        return None


def _shuffled_options(options: list, correct_index: int, rng: random.Random):
    indexed = list(enumerate(options))
    rng.shuffle(indexed)
    shuffled = []
    correct_key = "A"
    for position, (original_index, text) in enumerate(indexed):
        key = OPTION_KEYS[position]
        shuffled.append({"key": key, "text": text})
        if original_index == correct_index:
            correct_key = key
    return shuffled, correct_key


def _select_questions(skill_names: list, purpose: str = "BASELINE") -> list:
    questions = question_generation_service.prepare_questions(skill_names, purpose, MAX_QUESTIONS)
    return questions[:MAX_QUESTIONS]


def _create_assessment(user: dict, purpose: str, skill_names: list, title: str, related_id: str | None = None) -> dict:
    questions = _select_questions(skill_names, purpose)
    if len(questions) != MAX_QUESTIONS:
        raise AppError(
            "We could not prepare a complete 20-question assessment yet. Please try again or add more skills.",
            "NO_QUESTIONS",
            422,
        )
    time_limits = {"BASELINE": 1080, "SKILL_CHECK": 600, "CERTIFICATION": 720, "PROJECT": 900}
    return assessments_repo.create_assessment(
        {
            "user_id": user["_id"],
            "organization_id": user.get("organization_id"),
            "purpose": purpose,
            "title": title,
            "skill_names": skill_names,
            "question_ids": [q["_id"] for q in questions],
            "time_limit_seconds": time_limits.get(purpose, 900),
            "related_id": related_id,
        }
    )


def create_baseline(user: dict) -> dict:
    profile = profiles_repo.find_profile(user["_id"]) or profiles_repo.create_profile(
        user["_id"], user.get("organization_id"), user.get("role", "STUDENT")
    )
    skill_names = []
    career = catalog_repo.find_career(profile.get("target_career_id")) if profile.get("target_career_id") else None
    if career:
        skill_names.extend([item["skill_name"] for item in career.get("required_skills", [])])
    skill_names.extend([item["skill_name"] for item in profiles_repo.list_learner_skills(user["_id"])])
    ordered = []
    for name in skill_names:
        if name not in ordered:
            ordered.append(name)
    title = "Baseline assessment"
    if career:
        title = f"Baseline assessment for {career['name']}"
    return _create_assessment(user, "BASELINE", ordered[:8], title)


def create_skill_check(user: dict, skill_names: list, title: str | None = None) -> dict:
    cleaned = []
    for name in skill_names or []:
        name = clean_text(name, 80)
        if name and name not in cleaned:
            cleaned.append(name)
    if not cleaned:
        raise AppError("Choose at least one skill to practise.", "SKILLS_REQUIRED", 422)
    if len(cleaned) > 4:
        raise AppError("Choose up to four skills per skill check.", "TOO_MANY_SKILLS", 422)
    return _create_assessment(user, "SKILL_CHECK", cleaned, title or f"Skill check: {', '.join(cleaned)}")


def create_certification_check(user: dict, cert: dict) -> dict:
    return _create_assessment(
        user,
        "CERTIFICATION",
        cert.get("skills", []),
        f"Certification verification: {cert['name']}",
        related_id=cert["_id"],
    )


def create_project_check(user: dict, project: dict) -> dict:
    skills = project.get("skills") or project.get("technologies") or []
    if not skills:
        raise AppError("Add the technologies used in this project first.", "SKILLS_REQUIRED", 422)
    skill_names = []
    for skill in skills[:4]:
        name = clean_text(skill, 80)
        if name and name not in skill_names:
            skill_names.append(name)
            catalog_repo.create_question(
                {
                    "skill_name": name,
                    "difficulty": "INTERMEDIATE",
                    "question_type": "PRACTICAL_WRITTEN",
                    "prompt": (
                        f"Describe how you used {name} in the project '{project['name']}'. "
                        "Cover the architecture or approach, one technical challenge, and a measurable outcome."
                    ),
                    "correct_keywords": [name.lower(), "challenge", "outcome", "design", "test"],
                    "explanation": "Practical follow-up used to review project evidence.",
                    "points": 2,
                }
            )
    questions = catalog_repo.list_questions_for_skills(skill_names)
    practical = [q for q in questions if q.get("question_type") == "PRACTICAL_WRITTEN"][-len(skill_names):]
    if not practical:
        raise AppError("We could not prepare project questions.", "NO_QUESTIONS", 422)
    return assessments_repo.create_assessment(
        {
            "user_id": user["_id"],
            "organization_id": user.get("organization_id"),
            "purpose": "PROJECT",
            "title": f"Project follow-up: {project['name']}",
            "skill_names": skill_names,
            "question_ids": [q["_id"] for q in practical],
            "time_limit_seconds": 900,
            "related_id": project["_id"],
        }
    )


def start_attempt(user: dict, assessment_id: str) -> dict:
    assessment = assessments_repo.find_assessment(assessment_id, user["_id"])
    if not assessment:
        raise AppError("Assessment not found.", "ASSESSMENT_NOT_FOUND", 404)
    from flask import current_app

    max_attempts = current_app.config.get("MAX_ASSESSMENT_ATTEMPTS", 5)
    if assessments_repo.count_attempts_for_assessment(assessment_id, user["_id"]) >= max_attempts:
        raise AppError("You have reached the attempt limit for this assessment.", "ATTEMPT_LIMIT", 429)
    if assessments_repo.count_active_attempts(assessment_id, user["_id"]):
        raise AppError("You already have this assessment open. Please finish it first.", "ATTEMPT_ACTIVE", 409)

    questions = catalog_repo.find_questions_by_ids(assessment["question_ids"])
    order = {qid: index for index, qid in enumerate(assessment["question_ids"])}
    questions.sort(key=lambda q: order.get(q["_id"], 99))

    rng = _rng()
    snapshot = []
    answer_key = {}
    for question in questions:
        if question.get("question_type") == "PRACTICAL_WRITTEN":
            snapshot.append(
                {
                    "question_id": question["_id"],
                    "prompt": question["prompt"],
                    "skill_name": question["skill_name"],
                    "difficulty": question.get("difficulty", "INTERMEDIATE"),
                    "question_type": "PRACTICAL_WRITTEN",
                    "options": [],
                    "points": question.get("points", 2),
                }
            )
            answer_key[question["_id"]] = {"keywords": question.get("correct_keywords", [])}
            continue
        options = question.get("options", [])
        if isinstance(options, str):
            options = [o.strip() for o in options.split("|") if o.strip()]
        if len(options) < 2:
            continue
        correct_index = question.get("correct_option", 0)
        if isinstance(correct_index, str) and correct_index.upper() in OPTION_KEYS:
            correct_index = OPTION_KEYS.index(correct_index.upper())
        shuffled, correct_key = _shuffled_options(options, int(correct_index), rng)
        snapshot.append(
            {
                "question_id": question["_id"],
                "prompt": question["prompt"],
                "skill_name": question["skill_name"],
                "difficulty": question.get("difficulty", "EASY"),
                "question_type": question.get("question_type", "FACTUAL"),
                "options": shuffled,
                "points": question.get("points", 1),
            }
        )
        answer_key[question["_id"]] = {"correct_option": correct_key}

    if not snapshot:
        raise AppError("This assessment has no playable questions.", "NO_QUESTIONS", 422)

    attempt = assessments_repo.create_attempt(
        {
            "user_id": user["_id"],
            "organization_id": user.get("organization_id"),
            "assessment_id": assessment_id,
            "purpose": assessment["purpose"],
            "title": assessment["title"],
            "attempt_number": assessments_repo.count_attempts_for_assessment(assessment_id, user["_id"]) + 1,
            "questions": snapshot,
            "answer_key": answer_key,
            "expires_at": now_utc() + timedelta(seconds=assessment["time_limit_seconds"]),
        }
    )
    return attempt_view(attempt)


def attempt_view(attempt: dict) -> dict:
    if not attempt:
        raise AppError("Assessment attempt not found.", "ATTEMPT_NOT_FOUND", 404)
    questions = [
        {key: value for key, value in question.items() if key in {
            "question_id", "prompt", "skill_name", "difficulty", "question_type", "options", "points"
        }}
        for question in attempt.get("questions", [])
    ]
    return {
        "_id": attempt["_id"],
        "assessment_id": attempt["assessment_id"],
        "title": attempt["title"],
        "purpose": attempt["purpose"],
        "status": attempt["status"],
        "attempt_number": attempt.get("attempt_number", 1),
        "started_at": attempt.get("started_at"),
        "expires_at": attempt.get("expires_at"),
        "questions": questions,
        "score": attempt.get("score"),
        "topic_scores": attempt.get("topic_scores", {}),
    }


def get_attempt(user: dict, attempt_id: str) -> dict:
    attempt = assessments_repo.find_attempt(attempt_id, user["_id"])
    if not attempt:
        raise AppError("Assessment attempt not found.", "ATTEMPT_NOT_FOUND", 404)
    if attempt["status"] != "IN_PROGRESS":
        return result_view(attempt)
    return attempt_view(attempt)


def submit_answers(user: dict, attempt_id: str, payload: dict) -> dict:
    attempt = assessments_repo.find_attempt(attempt_id, user["_id"])
    if not attempt:
        raise AppError("Assessment attempt not found.", "ATTEMPT_NOT_FOUND", 404)
    if attempt["status"] != "IN_PROGRESS":
        raise AppError("This assessment has already been submitted.", "ALREADY_SUBMITTED", 409)

    submitted = payload.get("answers") or {}
    if not isinstance(submitted, dict):
        raise AppError("Answers must be an object keyed by question id.", "INVALID_ANSWERS", 422)
    valid_ids = {q["question_id"] for q in attempt.get("questions", [])}
    answers = []
    for question_id, answer in submitted.items():
        if question_id not in valid_ids:
            continue
        if isinstance(answer, dict):
            answers.append(
                {
                    "question_id": question_id,
                    "selected_option": clean_text(answer.get("selected_option"), 4).upper(),
                    "text_answer": clean_text(answer.get("text_answer"), 3000),
                }
            )
    if not answers:
        raise AppError("Please answer at least one question before submitting.", "NO_ANSWERS", 422)

    integrity = payload.get("integrity") or {}
    try:
        tab_switch_count = max(0, min(200, int(integrity.get("tab_switch_count", 0))))
        visibility_events = max(0, min(200, int(integrity.get("visibility_events", 0))))
    except (TypeError, ValueError):
        tab_switch_count = visibility_events = 0

    attempt["answers"] = answers
    attempt["submitted_at"] = now_utc()
    attempt["status"] = "SUBMITTED"
    attempt["integrity"] = {
        "tab_switch_count": tab_switch_count,
        "visibility_events": visibility_events,
        "client_events": [clean_text(e, 80) for e in (integrity.get("events") or [])][:50],
        "flags": [],
        "risk_level": "LOW",
    }
    assessments_repo.save_attempt(attempt)

    events = [
        {
            "attempt_id": attempt["_id"],
            "user_id": user["_id"],
            "event_type": "TAB_SWITCH",
            "detail": f"Tab switches reported: {tab_switch_count}",
            "at": now_utc(),
        },
        {
            "attempt_id": attempt["_id"],
            "user_id": user["_id"],
            "event_type": "VISIBILITY_CHANGE",
            "detail": f"Visibility changes reported: {visibility_events}",
            "at": now_utc(),
        },
    ]
    assessments_repo.add_integrity_events(events)
    ops_service.safe_log("assessment_submitted", attempt_id=attempt["_id"], purpose=attempt["purpose"])
    return {"attempt_id": attempt["_id"], "status": "SUBMITTED"}


def _score_written(text: str, keywords: list, points: float) -> dict:
    text_lower = (text or "").lower()
    keywords = [clean_text(k, 60).lower() for k in keywords if clean_text(k, 60)]
    matched = [keyword for keyword in keywords if keyword and keyword in text_lower]
    keyword_ratio = len(matched) / len(keywords) if keywords else 0
    length_factor = min(1.0, len(text_lower) / 240)
    ratio = 0.6 * keyword_ratio + 0.4 * length_factor
    return {
        "awarded": round(points * ratio, 2),
        "ratio": round(ratio, 3),
        "matched_keywords": matched,
        "needs_review": True,
    }


def evaluate_attempt(attempt_id: str) -> dict:
    attempt = assessments_repo.find_attempt(attempt_id)
    if not attempt:
        raise AppError("Assessment attempt not found.", "ATTEMPT_NOT_FOUND", 404)
    if attempt["status"] == "EVALUATED":
        return attempt

    answer_map = {a["question_id"]: a for a in attempt.get("answers", [])}
    answer_key = attempt.get("answer_key", {})
    per_skill_awarded = {}
    per_skill_total = {}
    total_awarded = 0.0
    total_points = 0.0
    breakdown = []

    for question in attempt.get("questions", []):
        qid = question["question_id"]
        skill = question["skill_name"]
        points = float(question.get("points", 1))
        per_skill_total[skill] = per_skill_total.get(skill, 0) + points
        total_points += points
        answer = answer_map.get(qid, {})
        key = answer_key.get(qid, {})
        awarded = 0.0
        correct = None
        if question.get("question_type") == "PRACTICAL_WRITTEN":
            scored = _score_written(answer.get("text_answer", ""), key.get("keywords", []), points)
            awarded = scored["awarded"]
        else:
            correct = answer.get("selected_option") == key.get("correct_option") and bool(answer.get("selected_option"))
            awarded = points if correct else 0.0
        per_skill_awarded[skill] = per_skill_awarded.get(skill, 0) + awarded
        total_awarded += awarded
        breakdown.append(
            {
                "question_id": qid,
                "skill_name": skill,
                "points_awarded": round(awarded, 2),
                "points_possible": points,
                "correct": correct,
            }
        )

    topic_scores = {}
    for skill, possible in per_skill_total.items():
        topic_scores[skill] = round(per_skill_awarded.get(skill, 0) / possible * 100) if possible else 0
    percentage = round(total_awarded / total_points * 100) if total_points else 0

    integrity = attempt.get("integrity", {})
    flags = []
    if integrity.get("tab_switch_count", 0) >= 3:
        flags.append({"code": "TAB_SWITCHING", "detail": "The assessment window lost focus several times."})
    if integrity.get("visibility_events", 0) >= 8:
        flags.append({"code": "FREQUENT_VISIBILITY_CHANGE", "detail": "The page was hidden repeatedly."})
    started = attempt.get("started_at")
    submitted = attempt.get("submitted_at")
    seconds = _seconds_between(started, submitted)
    if seconds is not None:
        expected = len(attempt.get("questions", [])) * 20
        if seconds < max(20, expected * 0.25):
            flags.append({"code": "FAST_SUBMISSION", "detail": "The assessment was submitted unusually quickly for human review."})
    selected = [a.get("selected_option") for a in attempt.get("answers", []) if a.get("selected_option")]
    if len(selected) >= 6 and len(set(selected)) == 1:
        flags.append({"code": "LOW_ANSWER_VARIANCE", "detail": "The same answer option was selected for many questions."})

    high = sum(1 for f in flags if f["code"] in {"TAB_SWITCHING", "FREQUENT_VISIBILITY_CHANGE"})
    risk_level = "HIGH" if high >= 2 else ("MEDIUM" if flags else "LOW")
    integrity["flags"] = flags
    integrity["risk_level"] = risk_level
    integrity["note"] = "Flags are for human review only. They are not proof of misconduct."

    if percentage >= 70:
        summary = "Strong result. You demonstrated solid understanding across most topics."
    elif percentage >= 50:
        summary = "A fair start. Some topics are already clear and a few need more practice."
    else:
        summary = "This topic needs more practice. Your learning plan will focus on the weaker areas."

    attempt["status"] = "EVALUATED"
    attempt["evaluated_at"] = now_utc()
    attempt["score"] = percentage
    attempt["topic_scores"] = topic_scores
    attempt["integrity"] = integrity
    attempt["summary"] = summary
    attempt["question_breakdown"] = breakdown
    assessments_repo.save_attempt(attempt)

    _apply_evidence(attempt, topic_scores, percentage)
    ops_service.safe_log(
        "assessment_evaluated", attempt_id=attempt_id, purpose=attempt["purpose"], score=percentage
    )
    return assessments_repo.find_attempt(attempt_id)


def _apply_evidence(attempt: dict, topic_scores: dict, overall: int) -> None:
    user_id = attempt["user_id"]
    org_id = attempt.get("organization_id")
    if attempt["purpose"] in {"BASELINE", "SKILL_CHECK"}:
        for skill, score in topic_scores.items():
            skill_service.add_evidence(
                user_id,
                org_id,
                skill,
                "ASSESSMENT",
                score,
                title=attempt["title"],
                source_id=attempt["_id"],
                verified=score >= 60,
            )
    elif attempt["purpose"] == "CERTIFICATION":
        cert = profiles_repo.find_certification(attempt.get("related_id") or "", user_id)
        if cert:
            passed = overall >= 60
            profiles_repo.update_certification(
                cert["_id"],
                {
                    "status": "VERIFIED" if passed else "FAILED",
                    "score": overall,
                    "verified_at": now_utc() if passed else None,
                },
            )
            if passed:
                for skill in cert.get("skills", []):
                    skill_service.add_evidence(
                        user_id,
                        org_id,
                        skill,
                        "CERTIFICATION",
                        topic_scores.get(skill, overall),
                        title=cert["name"],
                        source_id=cert["_id"],
                        verified=True,
                    )
    elif attempt["purpose"] == "PROJECT":
        project = profiles_repo.find_project(attempt.get("related_id") or "", user_id)
        if project:
            passed = overall >= 60
            profiles_repo.update_project(
                project["_id"],
                {
                    "status": "VERIFIED" if passed else "NEEDS_REVISION",
                    "verified_at": now_utc() if passed else None,
                    "ai_analysis": {
                        "follow_up_score": overall,
                        "topic_scores": topic_scores,
                        "summary": attempt.get("summary", ""),
                    },
                },
            )
            if passed:
                for skill in project.get("skills", []):
                    skill_service.add_evidence(
                        user_id,
                        org_id,
                        skill,
                        "PROJECT",
                        topic_scores.get(skill, overall),
                        title=project["name"],
                        source_id=project["_id"],
                        verified=True,
                    )


def result_view(attempt: dict) -> dict:
    questions = {q["question_id"]: q for q in attempt.get("questions", [])}
    answer_map = {a["question_id"]: a for a in attempt.get("answers", [])}
    items = []
    for item in attempt.get("question_breakdown", []):
        question = questions.get(item["question_id"], {})
        answer = answer_map.get(item["question_id"], {})
        key = attempt.get("answer_key", {}).get(item["question_id"], {})
        items.append(
            {
                "prompt": question.get("prompt", ""),
                "skill_name": item["skill_name"],
                "selected_option": answer.get("selected_option", ""),
                "text_answer": answer.get("text_answer", ""),
                "correct_option": key.get("correct_option", ""),
                "points_awarded": item["points_awarded"],
                "points_possible": item["points_possible"],
                "correct": item["correct"],
            }
        )
    return {
        "_id": attempt["_id"],
        "title": attempt["title"],
        "purpose": attempt["purpose"],
        "status": attempt["status"],
        "score": attempt.get("score"),
        "topic_scores": attempt.get("topic_scores", {}),
        "integrity": attempt.get("integrity", {}),
        "summary": attempt.get("summary", ""),
        "evaluated_at": attempt.get("evaluated_at"),
        "questions": items,
    }


def list_assessments_for(user: dict) -> dict:
    definitions = assessments_repo.list_assessments(user["_id"])
    attempts = assessments_repo.list_attempts(user["_id"])
    attempt_map = {}
    for attempt in attempts:
        attempt_map.setdefault(attempt["assessment_id"], []).append(attempt)
    return {
        "assessments": [
            {
                "assessment_id": item["_id"],
                "title": item["title"],
                "purpose": item["purpose"],
                "skill_names": item.get("skill_names", []),
                "time_limit_seconds": item.get("time_limit_seconds", 900),
                "created_at": item.get("created_at"),
                "attempts": [
                    {
                        "_id": a["_id"],
                        "status": a["status"],
                        "score": a.get("score"),
                        "attempt_number": a.get("attempt_number", 1),
                        "started_at": a.get("started_at"),
                        "evaluated_at": a.get("evaluated_at"),
                    }
                    for a in attempt_map.get(item["_id"], [])
                ],
            }
            for item in definitions
        ],
        "history": [
            {
                "_id": a["_id"],
                "title": a.get("title"),
                "purpose": a.get("purpose"),
                "status": a["status"],
                "score": a.get("score"),
                "risk_level": (a.get("integrity") or {}).get("risk_level", ""),
                "created_at": a.get("created_at"),
                "evaluated_at": a.get("evaluated_at"),
            }
            for a in attempts
        ],
    }
