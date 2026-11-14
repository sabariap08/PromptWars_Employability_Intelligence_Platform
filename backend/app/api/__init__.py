"""API blueprint registration."""
from app.api.admin import bp as admin_bp
from app.api.approvals import bp as approvals_bp
from app.api.assessments import bp as assessments_bp
from app.api.auth import bp as auth_bp
from app.api.learner import bp as learner_bp
from app.api.learning import bp as learning_bp
from app.api.mentor import bp as mentor_bp
from app.api.notifications import bp as notifications_bp
from app.api.organizations import bp as organizations_bp
from app.api.public import bp as public_bp

API_BLUEPRINTS = (
    auth_bp,
    public_bp,
    notifications_bp,
    approvals_bp,
    organizations_bp,
    learner_bp,
    assessments_bp,
    learning_bp,
    mentor_bp,
    admin_bp,
)


def register_api_blueprints(app) -> None:
    for blueprint in API_BLUEPRINTS:
        app.register_blueprint(blueprint)
