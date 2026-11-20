import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SubscriptionPlan, UserRole


class UserProfileResponse(BaseModel):
    """Public user profile information."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    avatar_url: Optional[str] = None
    department: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    timezone: str = "UTC"
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OrganizationMembershipResponse(BaseModel):
    """Organization summary and user's role within that tenant."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    logo_url: Optional[str] = None
    plan: SubscriptionPlan
    role: UserRole
    joined_at: datetime


class ActiveOrganizationDetailResponse(BaseModel):
    """Detailed view of the active organization context."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    logo_url: Optional[str] = None
    plan: SubscriptionPlan
    role: UserRole
    joined_at: datetime


class AuthMeResponse(BaseModel):
    """Complete authenticated session metadata."""

    user: UserProfileResponse
    active_organization: Optional[ActiveOrganizationDetailResponse] = None
    organizations: List[OrganizationMembershipResponse] = Field(default_factory=list)


class SwitchOrganizationRequest(BaseModel):
    """Request to switch active tenant organization context."""

    organization_id: uuid.UUID


class SwitchOrganizationResponse(BaseModel):
    """Result of switching organization context."""

    message: str
    active_organization: ActiveOrganizationDetailResponse


class TokenVerificationResponse(BaseModel):
    """Diagnostic response for token verification testing."""

    valid: bool
    user_id: uuid.UUID
    email: Optional[str] = None
    auth_role: str
    expires_at: datetime


class LoginRequest(BaseModel):
    """Payload for user sign in."""

    email: str
    password: Optional[str] = None


class SignupRequest(BaseModel):
    """Payload for user registration."""

    email: str
    password: str
    name: Optional[str] = None
    phone: Optional[str] = None
    workspace_name: Optional[str] = None
    workspace_slug: Optional[str] = None
    plan: Optional[str] = None


class UpdateProfileRequest(BaseModel):
    """Payload for updating user profile."""

    name: Optional[str] = None
    email: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    timezone: Optional[str] = None
    avatar_url: Optional[str] = None


class DemoSessionRequest(BaseModel):
    """Payload to initiate a session for demo personas."""

    user_id: Optional[uuid.UUID] = None
    email: Optional[str] = None


class AuthSessionResponse(BaseModel):
    """Session authentication response containing access token and user context."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    user: UserProfileResponse
    active_organization: Optional[ActiveOrganizationDetailResponse] = None
    organizations: List[OrganizationMembershipResponse] = Field(default_factory=list)
