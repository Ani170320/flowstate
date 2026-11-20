"""
API route definitions and router aggregator.
"""

from app.routes.activities import router as activities_router
from app.routes.attachments import router as attachments_router
from app.routes.auth import router as auth_router
from app.routes.calendar import router as calendar_router
from app.routes.comments import router as comments_router
from app.routes.dashboard import router as dashboard_router
from app.routes.health import router as health_router
from app.routes.labels import router as labels_router
from app.routes.notifications import router as notifications_router
from app.routes.organizations import router as organizations_router
from app.routes.projects import router as projects_router
from app.routes.ai import router as ai_router
from app.routes.tasks import router as tasks_router
from app.routes.teams import router as teams_router

__all__ = [
    "health_router",
    "auth_router",
    "organizations_router",
    "teams_router",
    "projects_router",
    "tasks_router",
    "labels_router",
    "comments_router",
    "attachments_router",
    "activities_router",
    "notifications_router",
    "calendar_router",
    "dashboard_router",
    "ai_router",
]
