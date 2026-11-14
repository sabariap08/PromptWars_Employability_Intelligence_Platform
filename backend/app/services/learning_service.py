"""Personalized roadmap generation and adaptive plan updates."""
from app.repositories import catalog_repo, learning_repo, profiles_repo
from app.services import career_service, scoring
from app.utils.ids import new_id
from app.utils.responses import AppError


def _resource_for(skill_name: str, proficiency: int) -> dict | None:
    resources = catalog_repo.find_resources_for_skill(skill_name)
    if not resources:
        return None
    preferred = scoring.difficulty_for_proficiency(proficiency)
    resources.sort(
        key=lambda resource: (
            0 if resource.get("difficulty") == preferred else 1,
            resource.get("duration_hours", 99),
        )
    )
    return resources[0]


def _exercise_for(skill_name: str) -> str:
    return (
        f"Build a small, self-contained deliverable that uses {skill_name}. "
        "Write a short note describing what you built, one problem you solved and how you tested it."
    )


def _gap_task(gap: dict, remediation: bool = False, reason: str = "") -> dict:
    proficiency = int(gap.get("current", 0))
    resource = _resource_for(gap["skill_name"], proficiency)
    if remediation:
        difficulty = "BEGINNER" if proficiency < 30 else "INTERMEDIATE"
        exercise = (
            f"Focused practice: redo two short exercises on the weak topics in {gap['skill_name']} "
            "and write down the rule or concept behind each mistake."
        )
    else:
        difficulty = scoring.difficulty_for_proficiency(proficiency)
        exercise = _exercise_for(gap["skill_name"])
    estimated = min(8.0, float(resource.get("duration_hours", 4))) if resource else 4.0
    return {
        "id": new_id(),
        "skill_name": gap["skill_name"],
        "resource_id": resource["_id"] if resource else None,
        "resource_title": resource["title"] if resource else f"Guided practice: {gap['skill_name']}",
        "resource_url": resource["url"] if resource else "",
        "provider": resource.get("provider", "") if resource else "",
        "resource_type": resource.get("resource_type", "PRACTICE") if resource else "PRACTICE",
        "difficulty": difficulty,
        "est_hours": estimated,
        "exercise": exercise,
        "checkpoint": f"Complete a {gap['skill_name']} skill check and score at least 70%.",
        "completion_criteria": "Finish the resource, complete the exercise, and pass the skill check.",
        "status": "PENDING",
        "self_reported": False,
        "remediation": remediation,
        "added_reason": reason,
        "completed_at": None,
    }


def _portfolio_task(career_name: str, focus_skills: list) -> dict:
    focus = ", ".join(focus_skills[:4]) if focus_skills else "your strongest skills"
    return {
        "id": new_id(),
        "skill_name": "Portfolio project",
        "resource_id": None,
        "resource_title": f"Portfolio project for {career_name}",
        "resource_url": "",
        "provider": "",
        "resource_type": "PROJECT",
        "difficulty": "INTERMEDIATE",
        "est_hours": 8.0,
        "exercise": (
            f"Create a portfolio-ready {career_name} project that demonstrates {focus}. "
            "Include a README with the problem, approach, trade-offs and measurable outcome."
        ),
        "checkpoint": "Submit the project for review and complete the project follow-up assessment.",
        "completion_criteria": "Project submitted with repository link or written evidence, then reviewed.",
        "status": "PENDING",
        "self_reported": False,
        "remediation": False,
        "added_reason": "",
        "completed_at": None,
    }


def _default_rationale(role: dict, readiness: int, gaps: list, strengths: list) -> str:
    parts = [f"Your current readiness for {role['name']} is {readiness}%."]
    if strengths:
        parts.append("Your strengths: " + ", ".join(item["skill_name"] for item in strengths[:3]) + ".")
    if gaps:
        parts.append(
            "We prioritised "
            + ", ".join(item["skill_name"] for item in gaps[:3])
            + " because they carry the biggest readiness impact."
        )
    else:
        parts.append("No critical gaps were found, so this plan focuses on portfolio evidence.")
    return " ".join(parts)


def generate_roadmap(user: dict, trigger: str = "initial", rationale: str = "") -> dict:
    profile = profiles_repo.find_profile(user["_id"])
    if not profile or not profile.get("target_career_id"):
        raise AppError("Choose a career goal before generating a roadmap.", "CAREER_REQUIRED", 422)
    role = catalog_repo.find_career(profile["target_career_id"])
    if not role:
        raise AppError("Your career goal is no longer available.", "CAREER_NOT_FOUND", 404)

    analysis = career_service.analyze_role(user["_id"], role)
    gaps = analysis["gaps"]
    missing = [gap for gap in gaps if gap["status"] == "MISSING"][:3]
    weak = [gap for gap in gaps if gap["status"] == "WEAK"][:4]
    other_missing = [gap for gap in gaps if gap["status"] == "MISSING"][3:5]

    phases = []
    phase_number = 1
    foundation = missing + (weak[:2] if not missing else [])
    if foundation:
        phases.append(
            {
                "phase_number": phase_number,
                "title": "Close the highest-impact gaps",
                "objective": "Build working knowledge in the skills that move your readiness the most.",
                "tasks": [_gap_task(gap) for gap in foundation],
            }
        )
        phase_number += 1

    strengthen = weak if missing else weak[2:]
    if other_missing:
        strengthen = other_missing + strengthen
    if strengthen:
        phases.append(
            {
                "phase_number": phase_number,
                "title": "Strengthen core skills",
                "objective": "Raise proven proficiency in skills you partially demonstrated.",
                "tasks": [_gap_task(gap) for gap in strengthen[:4]],
            }
        )
        phase_number += 1

    focus_skills = [item["skill_name"] for item in analysis["strengths"]] or [
        gap["skill_name"] for gap in gaps[:3]
    ]
    phases.append(
        {
            "phase_number": phase_number,
            "title": "Prove it with a project",
            "objective": "Turn new skills into visible, reviewable evidence.",
            "tasks": [_portfolio_task(role["name"], focus_skills)],
        }
    )

    estimated = round(
        sum(task["est_hours"] for phase in phases for task in phase["tasks"]), 1
    )
    learning_repo.archive_active_roadmaps(user["_id"])
    return learning_repo.create_roadmap(
        {
            "user_id": user["_id"],
            "organization_id": user.get("organization_id"),
            "career_role_id": role["_id"],
            "career_name": role["name"],
            "version": learning_repo.next_version(user["_id"]),
            "trigger": trigger,
            "rationale": rationale or _default_rationale(role, analysis["readiness"], gaps, analysis["strengths"]),
            "readiness_snapshot": analysis["readiness"],
            "phases": phases,
            "estimated_hours": estimated,
        }
    )


def _find_task(roadmap: dict, task_id: str):
    for phase in roadmap.get("phases", []):
        for task in phase.get("tasks", []):
            if task["id"] == task_id:
                return phase, task
    return None, None


def update_task(user: dict, task_id: str, action: str, evidence_url: str = "") -> dict:
    roadmap = learning_repo.active_roadmap(user["_id"])
    if not roadmap:
        raise AppError("You do not have an active learning plan yet.", "ROADMAP_NOT_FOUND", 404)
    _phase, task = _find_task(roadmap, task_id)
    if not task:
        raise AppError("Learning task not found.", "TASK_NOT_FOUND", 404)
    action = (action or "").upper()
    if action not in {"START", "COMPLETE", "REOPEN"}:
        raise AppError("Unsupported task action.", "INVALID_ACTION", 422)

    if action == "COMPLETE":
        if task["status"] != "COMPLETED":
            task["status"] = "COMPLETED"
            task["self_reported"] = True
            from app.utils.ids import now_utc

            task["completed_at"] = now_utc()
            learning_repo.record_activity(
                {
                    "user_id": user["_id"],
                    "organization_id": user.get("organization_id"),
                    "roadmap_id": roadmap["_id"],
                    "task_id": task["id"],
                    "task_title": task["resource_title"],
                    "skill_name": task["skill_name"],
                    "activity_type": "TASK",
                    "status": "COMPLETED",
                    "self_reported": True,
                    "evidence_url": evidence_url,
                    "hours": task.get("est_hours", 0),
                }
            )
    elif action == "START":
        if task["status"] == "PENDING":
            task["status"] = "IN_PROGRESS"
            learning_repo.record_activity(
                {
                    "user_id": user["_id"],
                    "organization_id": user.get("organization_id"),
                    "roadmap_id": roadmap["_id"],
                    "task_id": task["id"],
                    "task_title": task["resource_title"],
                    "skill_name": task["skill_name"],
                    "activity_type": "TASK",
                    "status": "IN_PROGRESS",
                    "self_reported": False,
                }
            )
    else:
        task["status"] = "PENDING"
        task["completed_at"] = None

    learning_repo.save_roadmap(roadmap)
    return roadmap


def next_tasks(roadmap: dict | None, limit: int = 3) -> list:
    if not roadmap:
        return []
    tasks = []
    for phase in roadmap.get("phases", []):
        for task in phase.get("tasks", []):
            if task.get("status") in {"PENDING", "IN_PROGRESS"}:
                tasks.append({**task, "phase_title": phase.get("title", "")})
    tasks.sort(key=lambda item: (0 if item["status"] == "IN_PROGRESS" else 1,))
    return tasks[:limit]


def roadmap_summary(roadmap: dict | None) -> dict:
    if not roadmap:
        return {"has_roadmap": False, "completion": 0, "total_tasks": 0, "completed_tasks": 0}
    tasks = [task for phase in roadmap.get("phases", []) for task in phase.get("tasks", [])]
    completed = sum(1 for task in tasks if task.get("status") == "COMPLETED")
    return {
        "has_roadmap": True,
        "_id": roadmap["_id"],
        "career_name": roadmap.get("career_name", ""),
        "version": roadmap.get("version", 1),
        "trigger": roadmap.get("trigger", ""),
        "rationale": roadmap.get("rationale", ""),
        "estimated_hours": roadmap.get("estimated_hours", 0),
        "readiness_snapshot": roadmap.get("readiness_snapshot", 0),
        "total_tasks": len(tasks),
        "completed_tasks": completed,
        "completion": round(completed / len(tasks) * 100) if tasks else 0,
        "next_tasks": next_tasks(roadmap),
        "generated_at": roadmap.get("created_at"),
    }


def adapt_after_assessment(user: dict, skill_name: str, score: int, weak_skills: list) -> dict | None:
    """Poor performance adds targeted revision; strong performance advances the plan."""
    roadmap = learning_repo.active_roadmap(user["_id"])
    if not roadmap:
        profile = profiles_repo.find_profile(user["_id"])
        if not profile or not profile.get("target_career_id"):
            return None
        roadmap = generate_roadmap(user, trigger="assessment")

    current = int((profiles_repo.find_learner_skill(user["_id"], skill_name) or {}).get("proficiency", 0))
    if score < 50:
        targets = weak_skills or [skill_name]
        existing = {
            (task.get("skill_name"), task.get("remediation"))
            for phase in roadmap.get("phases", [])
            for task in phase.get("tasks", [])
            if task.get("status") in {"PENDING", "IN_PROGRESS"}
        }
        new_tasks = []
        for target in targets[:2]:
            if (target, True) in existing:
                continue
            new_tasks.append(
                _gap_task(
                    {"skill_name": target, "current": current},
                    remediation=True,
                    reason=f"Added after a {score}% result in {skill_name}.",
                )
            )
        if new_tasks:
            if not roadmap["phases"]:
                roadmap["phases"] = [
                    {
                        "phase_number": 1,
                        "title": "Targeted revision",
                        "objective": "Revisit the concepts that need more practice.",
                        "tasks": [],
                    }
                ]
            roadmap["phases"][0]["tasks"] = new_tasks + roadmap["phases"][0]["tasks"]
            roadmap["version"] = int(roadmap.get("version", 1)) + 1
            roadmap["trigger"] = "poor_performance"
            roadmap["rationale"] = (
                f"We noticed {score}% in {skill_name}. Your plan now starts with focused revision on "
                + ", ".join(targets[:2])
                + ". Everything you already completed is still in place."
            )
            learning_repo.save_roadmap(roadmap)
            return {"roadmap": roadmap, "updated": True, "message": roadmap["rationale"]}
        return {"roadmap": roadmap, "updated": False, "message": "Your plan already includes targeted revision."}

    if score >= 75:
        changed = False
        for phase in roadmap.get("phases", []):
            for task in phase.get("tasks", []):
                if task.get("skill_name") == skill_name and task.get("remediation") and task["status"] != "COMPLETED":
                    task["status"] = "COMPLETED"
                    task["completion_source"] = "SKILL_CHECK"
                    changed = True
        advanced_exists = any(
            task.get("skill_name") == skill_name and task.get("difficulty") == "ADVANCED"
            for phase in roadmap.get("phases", [])
            for task in phase.get("tasks", [])
        )
        if not advanced_exists:
            resource = None
            for candidate in catalog_repo.find_resources_for_skill(skill_name):
                if candidate.get("difficulty") == "ADVANCED":
                    resource = candidate
                    break
            advanced = {
                "id": new_id(),
                "skill_name": skill_name,
                "resource_id": resource["_id"] if resource else None,
                "resource_title": resource["title"] if resource else f"Advanced challenge: {skill_name}",
                "resource_url": resource["url"] if resource else "",
                "provider": resource.get("provider", "") if resource else "",
                "resource_type": resource.get("resource_type", "PROJECT") if resource else "PROJECT",
                "difficulty": "ADVANCED",
                "est_hours": min(8.0, float(resource.get("duration_hours", 5))) if resource else 5.0,
                "exercise": f"Build an advanced {skill_name} feature and document the design decisions.",
                "checkpoint": f"Pass an advanced {skill_name} skill check.",
                "completion_criteria": "Deliverable submitted and reviewed.",
                "status": "PENDING",
                "self_reported": False,
                "remediation": False,
                "added_reason": f"Added because you scored {score}% in {skill_name}.",
                "completed_at": None,
            }
            insert_phase = roadmap["phases"][1] if len(roadmap["phases"]) > 1 else roadmap["phases"][0]
            insert_phase["tasks"].append(advanced)
            changed = True
        if changed:
            roadmap["version"] = int(roadmap.get("version", 1)) + 1
            roadmap["trigger"] = "strong_performance"
            roadmap["rationale"] = (
                f"Great work — {score}% in {skill_name}. We marked the revision tasks complete and added a "
                "more advanced challenge so you can keep growing."
            )
            learning_repo.save_roadmap(roadmap)
            return {"roadmap": roadmap, "updated": True, "message": roadmap["rationale"]}
    return {"roadmap": roadmap, "updated": False, "message": ""}


def mark_task_verified(user: dict, task_id: str) -> None:
    roadmap = learning_repo.active_roadmap(user["_id"])
    if not roadmap:
        return
    _, task = _find_task(roadmap, task_id)
    if task:
        task["status"] = "COMPLETED"
        task["self_reported"] = False
        from app.utils.ids import now_utc

        task["completed_at"] = now_utc()
        task["completion_source"] = "TRAINER"
        learning_repo.save_roadmap(roadmap)
