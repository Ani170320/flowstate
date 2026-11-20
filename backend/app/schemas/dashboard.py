import uuid
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict

from app.models.enums import PriorityLevel, ProjectStatus


class DashboardOverviewResponse(BaseModel):
    """High-level organization workspace KPI overview."""
    total_projects: int
    active_projects: int
    completed_projects: int
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    overdue_tasks: int
    upcoming_deadlines: int
    total_team_members: int
    my_tasks_summary: Dict[str, int]


class TaskStatsResponse(BaseModel):
    """Aggregated task statistics grouped by status, priority, and hours."""
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    overdue_tasks: int
    completion_rate: float
    tasks_by_status: Dict[str, int]
    tasks_by_priority: Dict[str, int]
    total_estimated_hours: float
    total_actual_hours: float


class ProjectStatItem(BaseModel):
    """Per-project health and progress statistics."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    name: str
    status: ProjectStatus
    priority: PriorityLevel
    color: str
    progress: int
    calculated_progress: int
    total_tasks: int
    completed_tasks: int
    overdue_tasks: int
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    is_overdue: bool = False
    spent: Decimal
    budget: Optional[Decimal] = None


class ProjectStatsResponse(BaseModel):
    """Collection of project health metrics across the workspace."""
    total_projects: int
    projects: List[ProjectStatItem]


class MemberWorkloadStatItem(BaseModel):
    """Workload and output metrics for an individual team member."""
    user_id: uuid.UUID
    name: str
    email: str
    avatar_url: Optional[str] = None
    role: Optional[str] = None
    assigned_tasks_count: int
    completed_tasks_count: int
    pending_tasks_count: int
    overdue_tasks_count: int
    workload_percentage: float


class TeamStatsResponse(BaseModel):
    """Organization-wide member workload distribution metrics."""
    total_members: int
    active_tasks_count: int
    members: List[MemberWorkloadStatItem]


class ProjectAnalyticsResponse(BaseModel):
    """Deep-dive analytics for a single project container."""
    project_id: uuid.UUID
    project_name: str
    project_key: str
    status: ProjectStatus
    priority: PriorityLevel
    completion_percentage: float
    tasks_by_status: Dict[str, int]
    tasks_by_priority: Dict[str, int]
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    overdue_tasks_count: int
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    days_remaining: Optional[int] = None
    is_overdue: bool = False
    estimated_hours_total: float
    actual_hours_total: float


class TeamAnalyticsResponse(BaseModel):
    """Team-specific member workload and execution metrics."""
    team_id: uuid.UUID
    team_name: str
    member_count: int
    members: List[MemberWorkloadStatItem]
