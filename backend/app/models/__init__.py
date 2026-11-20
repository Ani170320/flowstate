"""
SQLAlchemy ORM Models Package for FLOWSTATE.

All database models inherit from `Base` and are exported here for Alembic migrations.

16 Domain Models across 4 Modules:
- Module 1 (Identity & Multi-Tenancy):
    - User (Linked 1:1 to Supabase auth.users)
    - Organization (Tenant root)
    - OrganizationMember (RBAC memberships)
    - WorkspaceSettings (1:1 Tenant preferences)
- Module 2 (Teams & Projects):
    - Team (Functional teams)
    - TeamMember (Team memberships)
    - Project (Project containers)
    - ProjectMember (Project participation)
- Module 3 (Tasks & Kanban):
    - Task (Work items with compound FK tenant isolation)
    - Subtask (Checklist items)
    - Label (Categorization tags)
    - task_labels (Junction table)
- Module 4 (Collaboration & Tracking):
    - Comment (Task discussion threads)
    - Attachment (Storage metadata with target check)
    - Activity (Append-only audit trail)
    - Notification (User notification inbox)

6 PostgreSQL Domain Enums:
- SubscriptionPlan
- UserRole
- ProjectStatus
- PriorityLevel
- TaskStatus
- NotificationType
"""

from app.database.connection import Base
from app.models.enums import (
    NotificationType,
    PriorityLevel,
    ProjectStatus,
    SubscriptionPlan,
    TaskStatus,
    UserRole,
)
from app.models.organization import (
    Organization,
    OrganizationMember,
    WorkspaceSettings,
)
from app.models.user import User
from app.models.team import Team, TeamMember
from app.models.project import Project, ProjectMember
from app.models.task import Label, Subtask, Task, task_labels
from app.models.collaboration import Activity, Attachment, Comment, Notification

__all__ = [
    "Base",
    # Enums
    "SubscriptionPlan",
    "UserRole",
    "ProjectStatus",
    "PriorityLevel",
    "TaskStatus",
    "NotificationType",
    # Module 1: Identity & Multi-Tenancy
    "User",
    "Organization",
    "OrganizationMember",
    "WorkspaceSettings",
    # Module 2: Teams & Projects
    "Team",
    "TeamMember",
    "Project",
    "ProjectMember",
    # Module 3: Tasks & Kanban
    "Task",
    "Subtask",
    "Label",
    "task_labels",
    # Module 4: Collaboration & Tracking
    "Comment",
    "Attachment",
    "Activity",
    "Notification",
]
