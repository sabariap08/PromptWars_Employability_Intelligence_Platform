"""Tenant-safe analytics for administrators and the platform owner."""
from flask import current_app

from app.repositories import (
    assessments_repo,
    learning_repo,
    operations_repo,
    organizations_repo,
    profiles_repo,
    users_repo,
)
from app.security.auth import ROLE_EMPLOYEE, ROLE_STUDENT
from app.services import career_service


def _learner_rows(org_id: str, learner_role: str) -> list:
    learners, _ = users_repo.list_by_org(
        org_id, roles=[learner_role], statuses=["APPROVED"], page=1, page_size=1000
    )
    progress_map = {item["user_id"]: item for item in learning_repo.list_org_progress(org_id)}
    rows = []
    for learner in learners:
        progress = progress_map.get(learner["_id"])
        if progress:
            readiness = progress.get("career_readiness", 0)
            completion = progress.get("roadmap_completion", 0)
        else:
            analysis = career_service.analyze(learner["_id"]) or {}
            readiness = analysis.get("readiness", 0)
            summary = learning_repo.active_roadmap(learner["_id"])
            completion = 0
        rows.append(
            {
                "_id": learner["_id"],
                "full_name": learner.get("full_name"),
                "email": learner.get("email"),
                "department_id": learner.get("department_id"),
                "readiness": readiness,
                "roadmap_completion": completion,
                "account_status": learner.get("account_status"),
            }
        )
    return rows


def org_overview(org_id: str, org_type: str) -> dict:
    learner_role = ROLE_STUDENT if org_type == "UNIVERSITY" else ROLE_EMPLOYEE
    rows = _learner_rows(org_id, learner_role)
    departments = organizations_repo.list_departments(org_id)
    department_map = {dept["_id"]: dept["name"] for dept in departments}

    pending, pending_total = users_repo.list_by_org(
        org_id,
        roles=[learner_role],
        statuses=["PENDING_APPROVAL", "EMAIL_VERIFICATION_PENDING"],
        page=1,
        page_size=1000,
    )

    skill_counter = {}
    for skill in profiles_repo.list_org_skills(org_id):
        if skill.get("proficiency", 0) < skill.get("target_proficiency", 60):
            entry = skill_counter.setdefault(
                skill["skill_name"], {"skill_name": skill["skill_name"], "learners": 0, "total_proficiency": 0}
            )
            entry["learners"] += 1
            entry["total_proficiency"] += skill.get("proficiency", 0)
    common_gaps = sorted(skill_counter.values(), key=lambda item: -item["learners"])[:8]
    for gap in common_gaps:
        gap["average_proficiency"] = round(gap.pop("total_proficiency") / max(1, gap["learners"]))

    dept_stats = {}
    for row in rows:
        name = department_map.get(row["department_id"], "Unassigned")
        stat = dept_stats.setdefault(name, {"department": name, "learners": 0, "readiness_total": 0})
        stat["learners"] += 1
        stat["readiness_total"] += row["readiness"]
    department_breakdown = [
        {
            "department": item["department"],
            "learners": item["learners"],
            "average_readiness": round(item["readiness_total"] / max(1, item["learners"])),
        }
        for item in dept_stats.values()
    ]

    attempts = assessments_repo.list_org_attempts(org_id)
    scores = [a["score"] for a in attempts if a.get("score") is not None]
    average_readiness = round(sum(r["readiness"] for r in rows) / len(rows)) if rows else 0

    return {
        "learners_total": len(rows),
        "pending_requests": len(pending),
        "pending_total": pending_total,
        "average_readiness": average_readiness,
        "assessments_completed": len(attempts),
        "average_assessment_score": round(sum(scores) / len(scores)) if scores else 0,
        "common_gaps": common_gaps,
        "department_breakdown": department_breakdown,
        "top_learners": sorted(rows, key=lambda row: -row["readiness"])[:5],
        "needs_support": sorted(rows, key=lambda row: row["readiness"])[:5],
        "completion_average": round(sum(r["roadmap_completion"] for r in rows) / len(rows)) if rows else 0,
    }


def platform_overview() -> dict:
    org_status = organizations_repo.count_by_status()
    roles = users_repo.count_by_role()
    pending_orgs = organizations_repo.count_orgs({"approval_status": "PENDING_APPROVAL"})
    manager = current_app.extensions.get("ai_manager")
    providers = manager.status() if manager else []
    return {
        "organizations": {
            "total": organizations_repo.count_orgs(),
            "universities": organizations_repo.count_orgs({"organization_type": "UNIVERSITY"}),
            "companies": organizations_repo.count_orgs({"organization_type": "COMPANY"}),
            "pending": pending_orgs,
            "by_status": org_status,
        },
        "users": {
            "total": users_repo.count(),
            "by_role": roles,
            "pending_members": users_repo.count({"account_status": "PENDING_APPROVAL"}),
        },
        "agents": operations_repo.execution_stats(),
        "providers": providers,
        "database_mode": current_app.extensions.get("db_mode", "memory"),
    }


def learner_snapshot(learner: dict) -> dict:
    """Authorized, read-only learner summary for admins and experts."""
    analysis = career_service.analyze(learner["_id"]) or {}
    roadmap = learning_repo.active_roadmap(learner["_id"])
    tasks = [task for phase in (roadmap or {}).get("phases", []) for task in phase.get("tasks", [])]
    attempts = assessments_repo.list_attempts(learner["_id"])
    skills = profiles_repo.list_learner_skills(learner["_id"])
    return {
        "user": {
            "_id": learner["_id"],
            "full_name": learner.get("full_name"),
            "email": learner.get("email"),
            "department_id": learner.get("department_id"),
            "designation": learner.get("designation", ""),
            "is_expert": learner.get("is_expert", False),
        },
        "career": {
            "name": analysis.get("career_name", ""),
            "readiness": analysis.get("readiness", 0),
            "gaps": analysis.get("gaps", [])[:6],
            "strengths": analysis.get("strengths", [])[:6],
        },
        "skills": [
            {
                "skill_name": skill["skill_name"],
                "proficiency": skill.get("proficiency", 0),
                "confidence": skill.get("confidence", "LOW"),
                "verification_status": skill.get("verification_status", "SELF_REPORTED"),
                "evidence_count": skill.get("evidence_count", 0),
            }
            for skill in skills
        ],
        "roadmap": {
            "career_name": (roadmap or {}).get("career_name", ""),
            "completion": round(
                sum(1 for task in tasks if task.get("status") == "COMPLETED") / len(tasks) * 100
            ) if tasks else 0,
            "total_tasks": len(tasks),
        },
        "assessments": [
            {
                "_id": attempt["_id"],
                "title": attempt.get("title"),
                "score": attempt.get("score"),
                "status": attempt["status"],
                "risk_level": (attempt.get("integrity") or {}).get("risk_level", ""),
                "evaluated_at": attempt.get("evaluated_at"),
            }
            for attempt in attempts[:10]
        ],
    }


def org_learners_for_admin(org_id: str, org_type: str) -> list:
    learner_role = ROLE_STUDENT if org_type == "UNIVERSITY" else ROLE_EMPLOYEE
    return _learner_rows(org_id, learner_role)
