"""AI question generation with deterministic validation and bank fallback.

Questions are generated in a single structured response, checked locally for
shape, uniqueness and answer-key integrity, then reviewed by a second AI pass
before they are stored. If no provider is available (or either validation step
fails), the curated question bank is used instead so the learner journey never
depends on an external service.
"""
import hashlib
import random
import re

from flask import current_app

from app.repositories import catalog_repo

QUESTION_COUNT = 20
OPTION_KEYS = ["A", "B", "C", "D"]
DIFFICULTIES = {"EASY", "MEDIUM", "HARD"}
QUESTION_TYPES = {"FACTUAL", "SCENARIO", "PRACTICAL"}
GENERATOR_SYSTEM = (
    "You are a rigorous technical assessment author. Return only valid JSON. "
    "Never reveal the answer key inside a question prompt or option."
)
REVIEW_SYSTEM = (
    "You are an assessment quality reviewer. Reject questions that are ambiguous, "
    "duplicated, factually wrong, have missing options, or leak the answer. Return only JSON."
)


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _tokens(value: str) -> set:
    return {token for token in _normalize(value).split() if len(token) > 2}


def _similar(left: str, right: str) -> float:
    left_tokens, right_tokens = _tokens(left), _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _is_duplicate(prompt: str, existing_prompts: list) -> bool:
    normalized = _normalize(prompt)
    for item in existing_prompts:
        if normalized == _normalize(item):
            return True
        if _similar(prompt, item) >= 0.86:
            return True
    return False


def _generation_key(skill_names: list, purpose: str, count: int) -> str:
    raw = "|".join(sorted(_normalize(name) for name in skill_names))
    return hashlib.sha256(f"{purpose}:{count}:{raw}".encode("utf-8")).hexdigest()[:32]


def _coerce_options(raw_options) -> list:
    if isinstance(raw_options, dict):
        ordered = []
        for key in OPTION_KEYS:
            value = raw_options.get(key) or raw_options.get(key.lower())
            if value:
                ordered.append(str(value).strip())
        raw_options = ordered
    if not isinstance(raw_options, list):
        return []
    options = []
    for item in raw_options:
        if isinstance(item, dict):
            item = item.get("text") or item.get("value") or ""
        text = str(item or "").strip()
        if text:
            options.append(text[:500])
    if len(options) != 4:
        return []
    if len({text.casefold() for text in options}) != 4:
        return []
    return options


def _coerce_correct_option(value) -> str:
    if isinstance(value, bool):
        return ""
    if isinstance(value, int) and 0 <= value < len(OPTION_KEYS):
        return OPTION_KEYS[value]
    text = str(value or "").strip().upper()
    if text in OPTION_KEYS:
        return text
    return ""


def _validate_question(raw: dict, allowed_skills: dict, existing_prompts: list) -> dict | None:
    if not isinstance(raw, dict):
        return None
    prompt = str(raw.get("prompt") or "").strip()
    if len(prompt) < 12 or len(prompt) > 1000:
        return None
    if _is_duplicate(prompt, existing_prompts):
        return None
    options = _coerce_options(raw.get("options"))
    if not options:
        return None
    correct_option = _coerce_correct_option(raw.get("correct_option"))
    if not correct_option:
        return None
    prompt_lower = prompt.casefold()
    if "correct answer is" in prompt_lower or "answer key" in prompt_lower:
        return None
    correct_text = options[OPTION_KEYS.index(correct_option)].casefold()
    if correct_text and correct_text in prompt_lower:
        return None
    skill_name = str(raw.get("skill_name") or "").strip()
    canonical_skill = allowed_skills.get(_normalize(skill_name))
    if not canonical_skill:
        return None
    difficulty = str(raw.get("difficulty") or "MEDIUM").strip().upper()
    if difficulty not in DIFFICULTIES:
        difficulty = "MEDIUM"
    question_type = str(raw.get("question_type") or "SCENARIO").strip().upper()
    if question_type not in QUESTION_TYPES or question_type == "PRACTICAL":
        question_type = "SCENARIO"
    return {
        "skill_name": canonical_skill,
        "difficulty": difficulty,
        "question_type": question_type,
        "prompt": prompt,
        "options": options,
        "correct_option": correct_option,
        "explanation": str(raw.get("explanation") or "").strip()[:1000],
        "points": 2 if difficulty == "HARD" else 1,
    }


def _validate_generated(payload: dict, skill_names: list, existing_prompts: list, count: int) -> list:
    raw_questions = payload.get("questions") if isinstance(payload, dict) else None
    if not isinstance(raw_questions, list) or len(raw_questions) != count:
        return []
    allowed_skills = {_normalize(name): name for name in skill_names}
    accepted = []
    seen = list(existing_prompts)
    for raw in raw_questions:
        question = _validate_question(raw, allowed_skills, seen)
        if not question:
            return []
        accepted.append(question)
        seen.append(question["prompt"])
    return accepted if len(accepted) == count else []


def _review_generated(manager, questions: list) -> bool:
    payload = {
        "questions": [
            {
                "prompt": question["prompt"],
                "options": question["options"],
                "correct_option": question["correct_option"],
                "skill_name": question["skill_name"],
            }
            for question in questions
        ]
    }
    prompt = (
        "Review this 20-question assessment. Approve only if every question is clear, "
        "unambiguous, has exactly one defensible answer, all four options are plausible, "
        "and no prompt leaks its answer. Return "
        '{"approved": true|false, "issues": ["..."]}.\n\n'
        f"{payload}"
    )
    review = manager.generate_json(
        prompt,
        system=REVIEW_SYSTEM,
        fallback={},
        required_keys=("approved",),
    )
    if not review.get("_ai"):
        return True
    return review.get("approved") is not False


def _generate_with_ai(skill_names: list, purpose: str, count: int, existing_prompts: list) -> list:
    manager = current_app.extensions.get("ai_manager")
    generation_key = _generation_key(skill_names, purpose, count)
    if not manager or not getattr(manager, "order", None):
        return []
    prompt = (
        f"Create exactly {count} multiple-choice questions for a {purpose.lower()} assessment. "
        f"Use only these skills: {', '.join(skill_names)}.\n"
        "Return a single JSON object with this shape:\n"
        '{"questions":[{"skill_name":"Python","difficulty":"EASY|MEDIUM|HARD",'
        '"question_type":"FACTUAL|SCENARIO","prompt":"...","options":["...","...","...","..."],'
        '"correct_option":"A|B|C|D","explanation":"...","points":1}]}\n'
        "Rules: exactly 4 options per question; exactly one correct option; every prompt must be "
        "unique and must not contain its correct answer; distribute questions across the supplied "
        "skills; mix difficulties; no placeholders or meta commentary."
    )
    result = manager.generate_json(
        prompt,
        system=GENERATOR_SYSTEM,
        fallback={},
        required_keys=("questions",),
    )
    if not result.get("_ai"):
        return []
    questions = _validate_generated(result, skill_names, existing_prompts, count)
    if not questions:
        current_app.logger.warning("AI question set failed local validation; using curated bank")
        return []
    if not _review_generated(manager, questions):
        current_app.logger.warning("AI question set failed second-pass review; using curated bank")
        return []
    metadata = {
        "provider": result.get("_provider"),
        "model": result.get("_model"),
        "validated": True,
        "reviewed": True,
    }
    stored = []
    for question in questions:
        stored.append(
            catalog_repo.create_question(
                {
                    **question,
                    "source": "AI_GENERATED",
                    "generation_key": generation_key,
                    "generation": metadata,
                }
            )
        )
    return stored


def _fallback_bank(skill_names: list, count: int) -> list:
    pool = catalog_repo.list_questions_for_skills(skill_names)
    pool = [item for item in pool if item.get("question_type") != "PRACTICAL_WRITTEN"]
    if len(pool) < count:
        seen_ids = {item["_id"] for item in pool}
        for item in catalog_repo.list_all_questions():
            if item["_id"] in seen_ids or item.get("question_type") == "PRACTICAL_WRITTEN":
                continue
            pool.append(item)
            seen_ids.add(item["_id"])
    grouped = {}
    for question in pool:
        grouped.setdefault(question.get("skill_name", "General"), []).append(question)
    rng = random.Random()
    for questions in grouped.values():
        rng.shuffle(questions)
    buckets = list(grouped.values())
    rng.shuffle(buckets)
    selected = []
    seen_ids = set()
    index = 0
    while len(selected) < count and buckets:
        bucket = buckets[index % len(buckets)]
        if bucket:
            question = bucket.pop(0)
            if question["_id"] not in seen_ids:
                selected.append(question)
                seen_ids.add(question["_id"])
        if not any(buckets):
            break
        index += 1
    rng.shuffle(selected)
    return selected[:count]


def prepare_questions(skill_names: list, purpose: str, count: int = QUESTION_COUNT) -> list:
    cleaned = []
    for name in skill_names or []:
        name = str(name or "").strip()[:80]
        if name and name not in cleaned:
            cleaned.append(name)
    if not cleaned:
        return []

    key = _generation_key(cleaned, purpose, count)
    cached = catalog_repo.list_questions_by_generation_key(key)
    if len(cached) >= count:
        cached = cached[:count]
        random.Random().shuffle(cached)
        return cached

    existing_prompts = [item.get("prompt", "") for item in catalog_repo.list_all_questions()]
    generated = _generate_with_ai(cleaned, purpose, count, existing_prompts)
    if len(generated) == count:
        return generated

    return _fallback_bank(cleaned, count)
