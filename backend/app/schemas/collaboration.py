import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NotificationType
from app.schemas.auth import UserProfileResponse


# ---------------------------------------------------------------------------
# Comments Schemas
# ---------------------------------------------------------------------------

class CommentCreateRequest(BaseModel):
    """Payload for posting a discussion comment on a task."""
    content: str = Field(..., min_length=1, max_length=10000, description="Markdown formatted comment text")


class CommentUpdateRequest(BaseModel):
    """Payload for editing a comment."""
    content: str = Field(..., min_length=1, max_length=10000, description="Updated markdown comment text")


class CommentResponse(BaseModel):
    """Complete serialized representation of a task comment."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    author_id: Optional[uuid.UUID] = None
    author: Optional[UserProfileResponse] = None
    content: str
    created_at: datetime
    updated_at: datetime


class CommentListResponse(BaseModel):
    """Paginated collection of comments for a task."""
    items: List[CommentResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Attachments Schemas
# ---------------------------------------------------------------------------

class AttachmentResponse(BaseModel):
    """Metadata representation of an attached file pointing to Supabase Storage."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    task_id: Optional[uuid.UUID] = None
    comment_id: Optional[uuid.UUID] = None
    name: str
    storage_bucket: str
    storage_path: str
    file_size: int
    mime_type: str
    uploaded_by: Optional[uuid.UUID] = None
    uploader: Optional[UserProfileResponse] = None
    created_at: datetime
    download_url: Optional[str] = None


class AttachmentListResponse(BaseModel):
    """List of attachments associated with a task."""
    items: List[AttachmentResponse]
    total: int


# ---------------------------------------------------------------------------
# Activities Schemas
# ---------------------------------------------------------------------------

class ActivityResponse(BaseModel):
    """Audit log entry capturing state mutations and user events."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    user: Optional[UserProfileResponse] = None
    action: str
    target_type: str
    target_id: uuid.UUID
    target_title: str
    project_id: Optional[uuid.UUID] = None
    details: Dict[str, Any]
    created_at: datetime


class ActivityListResponse(BaseModel):
    """Paginated timeline of system activities."""
    items: List[ActivityResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Notifications Schemas
# ---------------------------------------------------------------------------

class NotificationResponse(BaseModel):
    """In-app notification item for user inbox."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    sender_id: Optional[uuid.UUID] = None
    sender: Optional[UserProfileResponse] = None
    type: NotificationType
    title: str
    message: str
    link: Optional[str] = None
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Paginated notification inbox with unread count."""
    items: List[NotificationResponse]
    total: int
    unread_count: int
    limit: int
    offset: int


class NotificationUnreadCountResponse(BaseModel):
    """Quick badge polling response for unread notifications."""
    unread_count: int


class NotificationBulkReadResponse(BaseModel):
    """Result of marking multiple notifications as read."""
    status: str = "success"
    updated_count: int
