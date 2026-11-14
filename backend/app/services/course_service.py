"""Course catalog, enrolment progress, recommendations and leaderboard."""
from app.repositories import (
    courses_repo,
    learning_repo,
    organizations_repo,
    profiles_repo,
    users_repo,
)
from app.security.auth import LEARNER_ROLES
from app.services import career_service, learning_service
from app.utils.ids import now_utc
from app.utils.responses import AppError

MAX_LEADERBOARD_USERS = 200


def _enrollment_map(user_id: str) -> dict:
    return {item["course_id"]: item for item in courses_repo.list_enrollments(user_id)}


def serialize_course(course: dict, enrollment: dict | None = None, include_modules: bool = False) -> dict:
    modules = course.get("modules", [])
    completed = set((enrollment or {}).get("completed_module_ids", []))
    item = {
        "_id": course["_id"],
        "title": course.get("title", ""),
        "provider": course.get("provider", ""),
        "description": course.get("description", ""),
        "url": course.get("url", ""),
        "difficulty": course.get("difficulty", "BEGINNER"),
        "duration_hours": course.get("duration_hours", 0),
        "skill_names": course.get("skill_names", []),
        "module_count": len(modules),
        "is_active": course.get("is_active", True),
        "enrollment": None,
    }
    if enrollment:
        item["enrollment"] = {
            "_id": enrollment["_id"],
            "status": enrollment.get("status", "ENROLLED"),
            "progress": enrollment.get("progress", 0),
            "completed_module_ids": sorted(completed),
            "started_at": enrollment.get("started_at"),
            "completed_at": enrollment.get("completed_at"),
        }
    if include_modules:
        item["modules"] = [
            {**module, "completed": module["id"] in completed}
            for module in modules
        ]
    return item


def list_courses(user: dict, search: str = "", skill: str = "", difficulty: str = "") -> list:
    enrollments = _enrollment_map(user["_id"])
    return [
        serialize_course(course, enrollments.get(course["_id"]))
        for course in courses_repo.list_courses(search=search, skill=skill, difficulty=difficulty)
    ]


def get_course(user: dict, course_id: str) -> dict:
    course = courses_repo.find_course(course_id)
    if not course or not course.get("is_active", True):
        raise AppError("Course not found.", "COURSE_NOT_FOUND", 404)
    enrollment = courses_repo.find_enrollment_for_course(user["_id"], course_id)
    return serialize_course(course, enrollment, include_modules=True)


def enroll(user: dict, course_id: str) -> dict:
    course = courses_repo.find_course(course_id, active_only=True)
    if not course:
        raise AppError("Course not found.", "COURSE_NOT_FOUND", 404)
    existing = courses_repo.find_enrollment_for_course(user["_id"], course_id)
    if existing:
        return {
            "enrollment": existing,
            "course": serialize_course(course, existing),
            "already_enrolled": True,
        }
    enrollment = courses_repo.create_enrollment(user, course)
    learning_repo.record_activity(
        {
            "user_id": user["_id"],
            "organization_id": user.get("organization_id"),
            "task_title": course.get("title", ""),
            "skill_name": ", ".join(course.get("skill_names", [])),
            "activity_type": "COURSE",
            "status": "IN_PROGRESS",
            "self_reported": False,
        }
    )
    return {
        "enrollment": enrollment,
        "course": serialize_course(course, enrollment, include_modules=True),
        "already_enrolled": False,
    }


def my_enrollments(user: dict) -> list:
    results = []
    for enrollment in courses_repo.list_enrollments(user["_id"]):
        course = courses_repo.find_course(enrollment["course_id"])
        if course:
            results.append(serialize_course(course, enrollment, include_modules=True))
    return results


def update_progress(user: dict, enrollment_id: str, module_id: str, completed: bool = True) -> dict:
    enrollment = courses_repo.find_enrollment(enrollment_id, user["_id"])
    if not enrollment:
        raise AppError("Enrolment not found.", "ENROLLMENT_NOT_FOUND", 404)
    course = courses_repo.find_course(enrollment["course_id"])
    if not course:
        raise AppError("Course not found.", "COURSE_NOT_FOUND", 404)
    modules = course.get("modules", [])
    if not any(module["id"] == module_id for module in modules):
        raise AppError("Module not found in this course.", "MODULE_NOT_FOUND", 404)

    completed_ids = set(enrollment.get("completed_module_ids", []))
    if completed:
        completed_ids.add(module_id)
    else:
        completed_ids.discard(module_id)

    total = len(modules) or 1
    progress = round(len(completed_ids) / total * 100)
    status = "COMPLETED" if len(completed_ids) >= len(modules) else "IN_PROGRESS"
    fields = {
        "completed_module_ids": sorted(completed_ids),
        "progress": progress,
        "status": status,
        "started_at": enrollment.get("started_at") or now_utc(),
        "completed_at": now_utc() if status == "COMPLETED" else None,
    }
    updated = courses_repo.update_enrollment(enrollment["_id"], fields)

    module_title = next((m["title"] for m in modules if m["id"] == module_id), "")
    learning_repo.record_activity(
        {
            "user_id": user["_id"],
            "organization_id": user.get("organization_id"),
            "task_title": f"{course.get('title', '')} — {module_title}",
            "skill_name": ", ".join(course.get("skill_names", [])),
            "activity_type": "COURSE",
            "status": "COMPLETED" if completed else "IN_PROGRESS",
            "self_reported": False,
            "hours": round(float(course.get("duration_hours", 0)) / total, 1),
        }
    )
    if status == "COMPLETED" and not any(
        item.get("source_type") == "COURSE" and item.get("source_id") == course["_id"]
        for item in profiles_repo.list_evidence(user["_id"])
    ):
        for skill_name in course.get("skill_names", []):
            profiles_repo.add_evidence(
                {
                    "user_id": user["_id"],
                    "organization_id": user.get("organization_id"),
                    "skill_name": skill_name,
                    "source_type": "COURSE",
                    "source_id": course["_id"],
                    "title": f"Completed {course.get('title', '')}",
                    "score": 70,
                    "verified": False,
                    "notes": f"{course.get('provider', '')} course completion.",
                }
            )
    return serialize_course(course, updated, include_modules=True)


def recommended_courses(user: dict, limit: int = 6) -> list:
    analysis = career_service.analyze(user["_id"]) or {}
    gap_skills = {row["skill_name"] for row in analysis.get("gaps", [])}
    strength_skills = {row["skill_name"] for row in analysis.get("strengths", [])}
    learner_skills = {row["skill_name"] for row in profiles_repo.list_learner_skills(user["_id"])}
    enrollments = _enrollment_map(user["_id"])
    scored = []
    for course in courses_repo.list_courses():
        enrollment = enrollments.get(course["_id"])
        if enrollment and enrollment.get("status") == "COMPLETED":
            continue
        skills = set(course.get("skill_names", []))
        gap_hits = sorted(skills & gap_skills)
        strength_hits = sorted(skills & strength_skills)
        owned_hits = sorted(skills & learner_skills)
        score = len(gap_hits) * 10 + len(strength_hits) * 3 + len(owned_hits) * 2
        if not skills:
            score += 0
        if score <= 0 and analysis:
            continue
        if gap_hits:
            reason = "Closes your " + ", ".join(gap_hits[:2]) + " gap"
        elif strength_hits:
            reason = "Deepens your " + ", ".join(strength_hits[:2]) + " strength"
        elif owned_hits:
            reason = "Builds on " + ", ".join(owned_hits[:2])
        else:
            reason = "Broadens your skill base"
        scored.append(
            {
                **serialize_course(course, enrollment),
                "match_score": score,
                "reason": reason,
            }
        )
    scored.sort(key=lambda item: (-item["match_score"], item["title"]))
    if not scored:
        scored = [
            {**serialize_course(course, enrollments.get(course["_id"])), "match_score": 0, "reason": "Explore a new skill"}
            for course in courses_repo.list_courses(limit=limit)
        ]
    return scored[:limit]


def _candidate_users(org_id: str | None) -> list:
    if org_id:
        items, _ = users_repo.list_by_org(
            org_id,
            roles=LEARNER_ROLES,
            statuses=["APPROVED"],
            page=1,
            page_size=MAX_LEADERBOARD_USERS,
        )
        return items
    items = []
    for role in LEARNER_ROLES:
        items.extend(users_repo.list_by_role(role, "APPROVED"))
    return items[:MAX_LEADERBOARD_USERS]


def leaderboard(user: dict, scope: str = "organization", limit: int = 20) -> dict:
    org_id = user.get("organization_id")
    if scope == "platform":
        org_id = None
    candidates = _candidate_users(org_id)
    rows = []
    for candidate in candidates:
        progress = learning_repo.find_progress(candidate["_id"]) or {}
        analysis = career_service.analyze(candidate["_id"]) or {}
        readiness = analysis.get("readiness", progress.get("career_readiness", 0)) or 0
        skills = profiles_repo.list_learner_skills(candidate["_id"])
        verified = sum(1 for skill in skills if skill.get("verification_status") == "VERIFIED")
        roadmap = learning_repo.active_roadmap(candidate["_id"])
        roadmap_completion = learning_service.roadmap_summary(roadmap).get("completion", 0) if roadmap else 0
        courses_completed = courses_repo.count_completed(candidate["_id"])
        average_score = progress.get("average_score", 0) or 0
        points = (
            float(readiness) * 0.5
            + float(average_score) * 0.25
            + verified * 2
            + float(roadmap_completion) * 0.15
            + courses_completed * 5
        )
        department = organizations_repo.find_department(candidate.get("department_id")) or {}
        rows.append(
            {
                "user_id": candidate["_id"],
                "full_name": candidate.get("full_name", ""),
                "department": department.get("name", ""),
                "readiness": round(readiness),
                "average_score": round(average_score),
                "skills_verified": verified,
                "courses_completed": courses_completed,
                "roadmap_completion": roadmap_completion,
                "points": round(points, 1),
            }
        )
    rows.sort(key=lambda item: (-item["points"], -item["readiness"], item["full_name"]))
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    me = next((row for row in rows if row["user_id"] == user["_id"]), None)
    return {
        "scope": scope if scope == "platform" else "organization",
        "leaderboard": rows[: max(1, min(50, limit))],
        "me": me,
        "total": len(rows),
        "organization_count": len(rows) if org_id else 0,
    }
