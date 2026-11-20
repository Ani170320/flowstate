import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import PriorityLevel, ProjectStatus
from app.schemas.auth import UserProfileResponse


class ProjectMemberResponse(BaseModel):
    """Enrolled project member detail with user profile."""

    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    user_id: uuid.UUID
    joined_at: datetime
    user: Optional[UserProfileResponse] = None


class AddProjectMemberRequest(BaseModel):
    """Payload to assign an organization user to a project."""

    user_id: Optional[uuid.UUID] = None
    email: Optional[str] = None


class ProjectCreateRequest(BaseModel):
    """Request payload for creating a new project container."""

    name: str = Field(..., min_length=2, max_length=255, description="Project title")
    key: Optional[str] = Field(None, min_length=2, max_length=10, pattern=r"^[A-Za-z0-9]+$", description="Uppercase task key prefix (e.g. 'FLW')")
    description: Optional[str] = Field(None, max_length=5000, description="Project charter / scope")
    team_id: Optional[uuid.UUID] = Field(None, description="Optional owning team ID")
    manager_id: Optional[uuid.UUID] = Field(None, description="Assigned project manager user ID")
    status: ProjectStatus = Field(default=ProjectStatus.PLANNING)
    priority: PriorityLevel = Field(default=PriorityLevel.MEDIUM)
    color: str = Field(default="#8B7CFF", pattern=r"^#[0-9a-fA-F]{6}$", description="Accent hex badge color")
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    budget: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0, description="Allocated budget")
    member_ids: Optional[List[uuid.UUID]] = Field(default_factory=list, description="Initial member assignments")

    @field_validator("due_date")
    @classmethod
    def validate_dates(cls, v: Optional[date], info) -> Optional[date]:
        start = info.data.get("start_date")
        if start and v and v < start:
            raise ValueError("due_date cannot be earlier than start_date.")
        return v


class ProjectUpdateRequest(BaseModel):
    """Request payload for updating project attributes."""

    name: Optional[str] = Field(None, min_length=2, max_length=255)
    key: Optional[str] = Field(None, min_length=2, max_length=10, pattern=r"^[A-Za-z0-9]+$")
    description: Optional[str] = Field(None, max_length=5000)
    team_id: Optional[uuid.UUID] = None
    manager_id: Optional[uuid.UUID] = None
    status: Optional[ProjectStatus] = None
    priority: Optional[PriorityLevel] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    budget: Optional[Decimal] = Field(None, ge=0)
    spent: Optional[Decimal] = Field(None, ge=0)

    @field_validator("due_date")
    @classmethod
    def validate_dates(cls, v: Optional[date], info) -> Optional[date]:
        start = info.data.get("start_date")
        if start and v and v < start:
            raise ValueError("due_date cannot be earlier than start_date.")
        return v


class ProjectResponse(BaseModel):
    """Comprehensive project container profile."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    team_id: Optional[uuid.UUID] = None
    key: str
    name: str
    description: Optional[str] = None
    status: ProjectStatus
    priority: PriorityLevel
    color: str
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    manager_id: Optional[uuid.UUID] = None
    manager: Optional[UserProfileResponse] = None
    progress: int = 0
    budget: Optional[Decimal] = Decimal("0.00")
    spent: Optional[Decimal] = Decimal("0.00")
    last_task_number: int = 100
    members_count: int = 0
    members: Optional[List[ProjectMemberResponse]] = None
    created_at: datetime
    updated_at: datetime
