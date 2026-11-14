"""Event-to-agent workflow definitions."""

WORKFLOWS = {
    "registration.approved": ["profile"],
    "profile.completed": ["profile", "assessment"],
    "assessment.submitted": [
        "assessment",
        "progress_evaluation",
        "skill_analysis",
        "career_intelligence",
        "learning_recommendation",
        "ai_mentor",
    ],
    "career.changed": [
        "career_intelligence",
        "skill_analysis",
        "learning_recommendation",
        "progress_evaluation",
        "ai_mentor",
    ],
    "certification.added": [
        "profile",
        "assessment",
        "skill_analysis",
        "career_intelligence",
        "learning_recommendation",
    ],
    "project.added": [
        "profile",
        "skill_analysis",
        "progress_evaluation",
        "career_intelligence",
        "assessment",
    ],
    "trainer.feedback": [
        "skill_analysis",
        "career_intelligence",
        "learning_recommendation",
    ],
}
