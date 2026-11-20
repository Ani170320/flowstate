import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base
from app.models.enums import NotificationType

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.project import Project
    from app.models.task import Task
    from app.models.user import User


class Comment(Base):
    """
    Threaded discussion records on tasks.
    """

    __tablename__ = "comments"
    __table_args__ = (
        Index("idx_comments_task_created", "task_id", "created_at"),
        Index("idx_comments_author_id", "author_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        doc="Comment primary key",
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        doc="Parent task foreign key",
    )

    author_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Author user foreign key",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Markdown formatted comment body",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        doc="Creation timestamp",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Last update timestamp",
    )

    # Relationships
    task: Mapped["Task"] = relationship("Task", back_populates="comments")
    author: Mapped[Optional["User"]] = relationship("User", foreign_keys=[author_id])
    attachments: Mapped[List["Attachment"]] = relationship("Attachment", back_populates="comment", cascade="all, delete-orphan")


class Attachment(Base):
    """
    Storage metadata pointing to Supabase Storage objects.
    Enforces polymorphic attachment validation via CHECK constraint.
    """

    __tablename__ = "attachments"
    __table_args__ = (
        CheckConstraint(
            "project_id IS NOT NULL OR task_id IS NOT NULL OR comment_id IS NOT NULL",
            name="chk_attachment_target",
        ),
        CheckConstraint(
            "file_size > 0",
            name="chk_attachment_positive_size",
        ),
        Index("idx_attachments_org_id", "organization_id"),
        Index("idx_attachments_project_id", "project_id"),
        Index("idx_attachments_task_id", "task_id"),
        Index("idx_attachments_comment_id", "comment_id"),
        Index("idx_attachments_uploaded_by", "uploaded_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        doc="Attachment primary key",
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        doc="Tenant organization foreign key",
    )

    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        doc="Associated project target",
    )

    task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True,
        doc="Associated task target",
    )

    comment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
        doc="Associated comment target",
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Original filename (e.g. 'architecture.pdf')",
    )

    storage_bucket: Mapped[str] = mapped_column(
        String(63),
        nullable=False,
        default="flowstate-attachments",
        server_default="flowstate-attachments",
        doc="Supabase Storage bucket name",
    )

    storage_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Storage path / key inside bucket",
    )

    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        doc="File size in bytes",
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="MIME type (e.g. 'application/pdf', 'image/png')",
    )

    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who uploaded file",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        doc="Upload timestamp",
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="attachments")
    task: Mapped[Optional["Task"]] = relationship("Task", back_populates="attachments")
    comment: Mapped[Optional["Comment"]] = relationship("Comment", back_populates="attachments")
    uploader: Mapped[Optional["User"]] = relationship("User", foreign_keys=[uploaded_by])


class Activity(Base):
    """
    Append-only audit trail logging user actions and state updates.
    """

    __tablename__ = "activities"
    __table_args__ = (
        Index("idx_activities_org_created", "organization_id", text("created_at DESC")),
        Index("idx_activities_project_created", "project_id", text("created_at DESC")),
        Index("idx_activities_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        doc="Activity record primary key",
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        doc="Tenant organization foreign key",
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Actor user who performed the action",
    )

    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Action identifier (e.g. 'created_task', 'status_change')",
    )

    target_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        doc="Entity type target ('task', 'project', 'team', 'comment')",
    )

    target_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        doc="Target entity ID",
    )

    target_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Human-readable title snapshot at action time",
    )

    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        doc="Optional project context",
    )

    details: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=dict,
        server_default="{}",
        doc="Event metadata / change diff payload",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        doc="Event timestamp",
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id])
    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="activities")


class Notification(Base):
    """
    Direct user notification inbox.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        Index("idx_notifications_user_unread", "user_id", text("created_at DESC")),
        Index("idx_notifications_user_all", "user_id", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        doc="Notification primary key",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Recipient user foreign key",
    )

    sender_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Actor/triggering user foreign key",
    )

    type: Mapped[NotificationType] = mapped_column(
        SQLEnum(
            NotificationType,
            name="notification_type",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        doc="Notification category",
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Notification headline",
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Notification body text",
    )

    link: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="In-app navigation link",
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        doc="Read status flag",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        doc="Notification timestamp",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    sender: Mapped[Optional["User"]] = relationship("User", foreign_keys=[sender_id])
