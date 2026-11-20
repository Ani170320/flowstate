import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import PriorityLevel, TaskStatus
from app.schemas.auth import UserProfileResponse


# ---------------------------------------------------------------------------
# Label Schemas
# ---------------------------------------------------------------------------

class LabelCreateRequest(BaseModel):
    """Payload to create an organization label."""

    name: str = Field(..., min_length=1, max_length=50, description="Label display text")
    color: str = Field(default="#8B7CFF", pattern=r"^#[0-9a-fA-F]{6}$", description="Badge hex color code")


class LabelUpdateRequest(BaseModel):
    """Payload to update an organization label."""

    name: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")


class LabelResponse(BaseModel):
    """Organization categorization label response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    color: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Subtask Schemas
# ---------------------------------------------------------------------------

class SubtaskCreateRequest(BaseModel):
    """Payload to add a checklist item to a task."""

    title: str = Field(..., min_length=1, max_length=255, description="Checklist item text")
    completed: bool = Field(default=False)


class SubtaskUpdateRequest(BaseModel):
    """Payload to modify a subtask item."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    completed: Optional[bool] = None
    order: Optional[int] = None


class SubtaskResponse(BaseModel):
    """Embedded checklist item detail."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    title: str
    completed: bool
    order: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Task Schemas
# ---------------------------------------------------------------------------

class TaskCreateRequest(BaseModel):
    """Payload for creating a new work item inside a project."""

    title: str = Field(..., min_length=1, max_length=255, description="Task summary")
    description: Optional[str] = Field(default="", description="Markdown task description")
    status: TaskStatus = Field(default=TaskStatus.TODO)
    priority: PriorityLevel = Field(default=PriorityLevel.MEDIUM)
    assignee_id: Optional[uuid.UUID] = Field(None, description="Assigned organization user ID")
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[Decimal] = Field(None, ge=0)
    actual_hours: Optional[Decimal] = Field(None, ge=0)
    order: Optional[float] = None
    label_ids: Optional[List[uuid.UUID]] = Field(default_factory=list)

    @field_validator("due_date")
    @classmethod
    def validate_dates(cls, v: Optional[date], info) -> Optional[date]:
        start = info.data.get("start_date")
        if start and v and v < start:
            raise ValueError("due_date cannot be earlier than start_date.")
        return v


class TaskUpdateRequest(BaseModel):
    """Payload for modifying an existing task."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[PriorityLevel] = None
    assignee_id: Optional[uuid.UUID] = None
    unassign: Optional[bool] = Field(default=False, description="Set True to clear task assignee")
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[Decimal] = Field(None, ge=0)
    actual_hours: Optional[Decimal] = Field(None, ge=0)
    order: Optional[float] = None

    @field_validator("due_date")
    @classmethod
    def validate_dates(cls, v: Optional[date], info) -> Optional[date]:
        start = info.data.get("start_date")
        if start and v and v < start:
            raise ValueError("due_date cannot be earlier than start_date.")
        return v


class TaskStatusUpdateRequest(BaseModel):
    """Payload for moving task to a different Kanban status column."""

    status: TaskStatus


class TaskPositionUpdateRequest(BaseModel):
    """Payload for reordering or moving a task in the Kanban board."""

    status: Optional[TaskStatus] = None
    order: Optional[float] = None
    before_task_id: Optional[uuid.UUID] = None
    after_task_id: Optional[uuid.UUID] = None


class TaskResponse(BaseModel):
    """Comprehensive work item detail."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    task_number: int
    key: str
    title: str
    description: str = ""
    status: TaskStatus
    priority: PriorityLevel
    assignee_id: Optional[uuid.UUID] = None
    assignee: Optional[UserProfileResponse] = None
    creator_id: Optional[uuid.UUID] = None
    creator: Optional[UserProfileResponse] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[Decimal] = None
    actual_hours: Optional[Decimal] = None
    order: float
    labels: Optional[List[LabelResponse]] = None
    subtasks: Optional[List[SubtaskResponse]] = None
    subtasks_count: int = 0
    subtasks_completed_count: int = 0
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Kanban Board Schemas
# ---------------------------------------------------------------------------

class KanbanColumnResponse(BaseModel):
    """Column bucket on the Kanban board."""

    status: TaskStatus
    tasks_count: int
    tasks: List[TaskResponse]


class KanbanBoardResponse(BaseModel):
    """Full Kanban board representation for a project."""

    project_id: uuid.UUID
    total_tasks: int
    columns: Dict[str, KanbanColumnResponse]
