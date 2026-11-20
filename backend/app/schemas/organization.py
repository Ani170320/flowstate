import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import SubscriptionPlan, UserRole
from app.schemas.auth import UserProfileResponse


class WorkspaceSettingsResponse(BaseModel):
    """Workspace settings for a tenant organization."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    currency: str = "USD"
    timezone: str = "UTC"
    working_days: List[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5])
    notifications_email: bool = True
    notifications_desktop: bool = True
    theme: str = "dark"
    accent_color: str = "#6366F1"
    updated_at: datetime


class WorkspaceSettingsUpdateRequest(BaseModel):
    """Fields permitted for updating workspace settings."""

    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    timezone: Optional[str] = Field(None, min_length=2, max_length=50)
    working_days: Optional[List[int]] = None
    notifications_email: Optional[bool] = None
    notifications_desktop: Optional[bool] = None
    theme: Optional[str] = Field(None, max_length=20)
    accent_color: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")

    @field_validator("working_days")
    @classmethod
    def validate_working_days(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        if v is not None:
            if not v:
                raise ValueError("working_days must contain at least one day (1=Monday to 7=Sunday).")
            for day in v:
                if day < 1 or day > 7:
                    raise ValueError(f"Invalid day {day}. Working days must be between 1 and 7.")
        return v


class OrganizationMemberResponse(BaseModel):
    """Enrolled organization member detail."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    role: UserRole
    joined_at: datetime
    user: Optional[UserProfileResponse] = None


class AddMemberRequest(BaseModel):
    """Request to enroll a user into an organization."""

    email: Optional[str] = None
    name: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None
    user_id: Optional[uuid.UUID] = None
    role: UserRole = UserRole.DEVELOPER


class UpdateMemberRoleRequest(BaseModel):
    """Request to alter a member's RBAC role within an organization."""

    role: UserRole


class OrganizationCreateRequest(BaseModel):
    """Request payload for creating a new tenant organization."""

    name: str = Field(..., min_length=2, max_length=255, description="Organization display name")
    slug: Optional[str] = Field(None, min_length=2, max_length=255, pattern=r"^[a-z0-9-]+$", description="URL-safe unique identifier")
    logo_url: Optional[str] = Field(None, max_length=500)
    plan: Optional[SubscriptionPlan] = Field(default=SubscriptionPlan.FREE, description="Requested tier - new workspaces must start on Free")


class OrganizationUpdateRequest(BaseModel):
    """Request payload for modifying organization details."""

    name: Optional[str] = Field(None, min_length=2, max_length=255)
    slug: Optional[str] = Field(None, min_length=2, max_length=255, pattern=r"^[a-z0-9-]+$")
    logo_url: Optional[str] = Field(None, max_length=500)
    plan: Optional[SubscriptionPlan] = Field(None, description="Plan updates cannot be made directly; managed by billing workflows")


class OrganizationBillingPlanUpdateRequest(BaseModel):
    """Payload for server-side trusted billing process to update plan."""

    plan: SubscriptionPlan


class OrganizationDetailResponse(BaseModel):
    """Comprehensive organization profile with member and settings context."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    logo_url: Optional[str] = None
    plan: SubscriptionPlan
    current_user_role: Optional[UserRole] = None
    members_count: int = 1
    settings: Optional[WorkspaceSettingsResponse] = None
    created_at: datetime
    updated_at: datetime
