"""AI Mentor with deterministic, data-grounded fallback responses."""
from flask import current_app

from app.repositories import learning_repo
from app.services import context_service
from app.utils.responses import AppError
from app.utils.text import clean_text

SYSTEM_PROMPT = (
    "You are the EIP learning mentor. Be supportive, concise and specific. "
    "Use only the context provided. Never invent scores, skills or courses. "
    "Keep answers under 180 words and end with one clear next step."
)


def _fallback_reply(message: str, context: dict) -> str:
    name = context["first_name"]
    career = context["career_name"] or "your chosen career"
    gaps = context["top_gaps"]
    next_tasks = context["next_tasks"]
    lowered = message.lower()

    gap_text = ""
    if gaps:
        gap_text = "Right now the biggest opportunities are " + ", ".join(
            f"{gap['skill']} ({gap['current']}% vs {gap['required']}% needed)" for gap in gaps[:2]
        ) + "."

    if "why" in lowered and ("plan" in lowered or "changed" in lowered or "roadmap" in lowered):
        rationale = context.get("plan_rationale") or "your latest results and evidence changed."
        return (
            f"{name}, your plan changed because {rationale} "
            f"Your readiness for {career} is currently {context['readiness']}%. "
            "Previously completed tasks were kept. "
            + (f"Next, start with '{next_tasks[0]['title']}'." if next_tasks else "Add evidence to refresh your plan.")
        )
    if "score" in lowered or "assessment" in lowered or "result" in lowered:
        if context.get("latest_score") is None:
            return (
                f"{name}, you have not completed an assessment yet. Start your baseline assessment so we can "
                f"measure your skills against {career} requirements, then I can give specific advice."
            )
        return (
            f"{name}, your latest result in {context.get('latest_assessment')} was {context['latest_score']}%. "
            f"{gap_text} A good next step is to finish the next task in your plan: "
            f"'{next_tasks[0]['title']}'." if next_tasks else
            f"{name}, your latest result was {context['latest_score']}%. Add a project or certification to strengthen your evidence."
        )
    if "next" in lowered or "what should i" in lowered or "start" in lowered:
        if next_tasks:
            first = next_tasks[0]
            return (
                f"{name}, your next step is '{first['title']}' for {first['skill']} "
                f"(about {first['hours']} hours). {gap_text} "
                f"Complete it, then take the related skill check so your readiness updates."
            )
        return (
            f"{name}, add a target career, skills and one piece of evidence first. "
            "Then I can build a personal plan and recommend the next task."
        )
    if "readiness" in lowered or "ready" in lowered or "gap" in lowered:
        return (
            f"{name}, your readiness for {career} is {context['readiness']}%. "
            f"{gap_text} You currently have {context['verified_skills']} verified skill(s) out of {context['total_skills']}. "
            + (f"Focus next on '{next_tasks[0]['title']}'." if next_tasks else "Take a skill check to verify more skills.")
        )
    return (
        f"{name}, I can help with your skill gaps, readiness, assessments and learning plan. "
        f"Your readiness for {career} is {context['readiness']}%. {gap_text} "
        + (f"Suggested next action: '{next_tasks[0]['title']}'." if next_tasks else
           "Suggested next action: generate your baseline assessment in the Assessments page.")
    )


def suggestions(context: dict) -> list:
    items = ["What should I do next?", "Why did my plan change?"]
    if context.get("latest_score") is not None:
        items.append("How can I improve my latest score?")
    items.append("How ready am I for my target career?")
    return items[:4]


def chat(user: dict, message: str) -> dict:
    message = clean_text(message, 1200)
    if not message:
        raise AppError("Please type a question for your mentor.", "MESSAGE_REQUIRED", 422)
    context = context_service.build(user)
    fallback = _fallback_reply(message, context)

    prompt = (
        f"Learner context (authoritative): {context}\n\n"
        f"Learner question: {message}\n\n"
        "Write a friendly, specific reply using only these facts."
    )
    manager = current_app.extensions.get("ai_manager")
    response = {"text": fallback, "provider": "deterministic-fallback", "model": "rules", "ok": False}
    if manager:
        response = manager.generate_text(prompt, system=SYSTEM_PROMPT, fallback_text=fallback)
    reply = clean_text(response.get("text") or fallback, 2000)

    learning_repo.append_message(
        user["_id"],
        user.get("organization_id"),
        {"role": "user", "content": message},
    )
    learning_repo.append_message(
        user["_id"],
        user.get("organization_id"),
        {
            "role": "assistant",
            "content": reply,
            "provider": response.get("provider", "deterministic-fallback"),
            "model": response.get("model", "rules"),
        },
    )
    return {
        "reply": reply,
        "provider": response.get("provider", "deterministic-fallback"),
        "suggestions": suggestions(context),
        "context": {
            "career_name": context.get("career_name"),
            "readiness": context.get("readiness"),
            "next_tasks": context.get("next_tasks"),
            "top_gaps": context.get("top_gaps"),
        },
    }


def history(user: dict) -> list:
    conversation = learning_repo.get_conversation(user["_id"])
    if not conversation:
        context = context_service.build(user)
        return [
            {
                "role": "assistant",
                "content": _fallback_reply("hello", context),
                "provider": "deterministic-fallback",
            }
        ]
    return conversation.get("messages", [])

def explain_change(context: dict, event: str, details: dict) -> str:
    """Friendly, deterministic change explanations for notifications."""
    name = context.get("first_name", "there")
    if event == "assessment.submitted":
        score = details.get("score")
        title = details.get("assessment_title", "your assessment")
        weak = details.get("weak_skills") or []
        if score is not None and score < 50:
            focus = ", ".join(weak[:2]) or context.get("career_name") or "the weak topics"
            return (
                f"{name}, you scored {score}% in {title}. That's okay — we found a few concepts that need "
                f"more practice, so we added focused revision on {focus}. Your previous progress is kept."
            )
        if score is not None and score >= 75:
            return (
                f"{name}, great work — {score}% in {title}. We marked related revision tasks complete and "
                "added a more advanced challenge so you keep growing."
            )
        return f"{name}, your {title} result was {score}%. We updated your skill evidence and kept your plan on track."
    if event == "career.changed":
        return (
            f"{name}, your career goal changed to {details.get('career_name', 'a new path')}. "
            "We reused your verified skills, rebuilt the roadmap and kept your completed learning history."
        )
    if event == "certification.added":
        return (
            f"{name}, we received your certification evidence for {details.get('name', 'your certification')}. "
            "A short verification check was created. Your readiness will update after you complete it."
        )
    if event == "project.added":
        return (
            f"{name}, your project '{details.get('name', 'project')}' was analysed and added as evidence. "
            "A follow-up assessment can strengthen verification."
        )
    if event == "trainer.feedback":
        return (
            f"{name}, a trainer reviewed your work on {details.get('skill_name', 'a skill')}. "
            "The feedback is now part of your verified evidence."
        )
    return f"{name}, your learning analysis was refreshed using your latest evidence."
