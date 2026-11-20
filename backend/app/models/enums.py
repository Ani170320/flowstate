import enum


class UserRole(str, enum.Enum):
    """Organization membership roles for Role-Based Access Control (RBAC)."""

    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    DEVELOPER = "developer"
    DESIGNER = "designer"
    VIEWER = "viewer"


class SubscriptionPlan(str, enum.Enum):
    """Organization billing and subscription tiers."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class ProjectStatus(str, enum.Enum):
    """Lifecycle states for projects."""

    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"


class PriorityLevel(str, enum.Enum):
    """Priority urgency ranking for projects and tasks."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, enum.Enum):
    """Workflow columns for tasks and Kanban boards."""

    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"


class NotificationType(str, enum.Enum):
    """Categorization for notifications."""

    ASSIGNMENT = "assignment"
    DEADLINE = "deadline"
    MENTION = "mention"
    PROJECT_UPDATE = "project_update"
    SYSTEM = "system"
