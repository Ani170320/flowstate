import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.auth import UserProfileResponse


class TeamMemberResponse(BaseModel):
    """Enrolled team member detail with user profile."""

    model_config = ConfigDict(from_attributes=True)

    team_id: uuid.UUID
    user_id: uuid.UUID
    joined_at: datetime
    user: Optional[UserProfileResponse] = None


class AddTeamMemberRequest(BaseModel):
    """Payload to enroll an organization user into a team."""

    user_id: Optional[uuid.UUID] = None
    email: Optional[str] = None


class TeamCreateRequest(BaseModel):
    """Request payload for creating a functional team within an organization."""

    name: str = Field(..., min_length=2, max_length=150, description="Team display name")
    description: Optional[str] = Field(None, max_length=2000, description="Team description or charter")
    lead_id: Optional[uuid.UUID] = Field(None, description="User identifier of team lead")
    member_ids: Optional[List[uuid.UUID]] = Field(default_factory=list, description="Initial member user IDs")


class TeamUpdateRequest(BaseModel):
    """Request payload for modifying team details."""

    name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    lead_id: Optional[uuid.UUID] = None


class TeamResponse(BaseModel):
    """Comprehensive team profile with lead and member details."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: Optional[str] = None
    lead_id: Optional[uuid.UUID] = None
    lead: Optional[UserProfileResponse] = None
    members_count: int = 0
    members: Optional[List[TeamMemberResponse]] = None
    created_at: datetime
    updated_at: datetime
