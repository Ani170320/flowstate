import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Double,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base
from app.models.enums import PriorityLevel, TaskStatus

if TYPE_CHECKING:
    from app.models.collaboration import Attachment, Comment
    from app.models.organization import Organization
    from app.models.project import Project
    from app.models.user import User

# Association table between tasks and labels
task_labels = Table(
    "task_labels",
    Base.metadata,
    Column("task_id", Uuid, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("label_id", Uuid, ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True),
    Index("idx_task_labels_label_id", "label_id"),
)


class Task(Base):
    """
    Work item rendered on Kanban boards, list views, and team backlogs.
    Enforces compound foreign key tenant isolation via (project_id, organization_id).
    """

    __tablename__ = "tasks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "organization_id"],
            ["projects.id", "projects.organization_id"],
            ondelete="CASCADE",
            name="fk_tasks_project_org",
        ),
        UniqueConstraint("id", "organization_id", name="uq_tasks_id_org"),
        UniqueConstraint("project_id", "task_number", name="uq_tasks_proj_number"),
        Index("idx_tasks_project_status_order", "project_id", "status", "order"),
        Index("idx_tasks_assignee_status", "assignee_id", "status"),
        Index("idx_tasks_org_status", "organization_id", "status"),
        Index("idx_tasks_due_date", "due_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        doc="Task primary key",
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        doc="Tenant organization foreign key",
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        doc="Project foreign key (part of compound FK)",
    )

    task_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Sequential task sequence number within the project",
    )

    key: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        doc="Formatted project task identifier (e.g. 'FLW-104')",
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Task summary title",
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
        doc="Markdown formatted task description",
    )

    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(
            TaskStatus,
            name="task_status",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=TaskStatus.TODO,
        server_default="todo",
        doc="Kanban status column",
    )

    priority: Mapped[PriorityLevel] = mapped_column(
        SQLEnum(
            PriorityLevel,
            name="priority_level",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=PriorityLevel.MEDIUM,
        server_default="medium",
        doc="Task urgency ranking",
    )

    assignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Assigned user",
    )

    creator_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who created the task",
    )

    start_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="Planned start date",
    )

    due_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="Task deadline date",
    )

    estimated_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2),
        nullable=True,
        doc="Estimated work in hours",
    )

    actual_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2),
        nullable=True,
        doc="Logged work in hours",
    )

    order: Mapped[float] = mapped_column(
        Float().with_variant(Double(), "postgresql"),
        nullable=False,
        default=1000.0,
        server_default="1000.0",
        doc="Fractional position for Kanban column reordering",
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
    organization: Mapped["Organization"] = relationship("Organization", foreign_keys=[organization_id], overlaps="project,tasks")
    project: Mapped["Project"] = relationship("Project", back_populates="tasks", foreign_keys=[project_id], overlaps="organization,tasks")
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assignee_id])
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[creator_id])
    subtasks: Mapped[List["Subtask"]] = relationship("Subtask", back_populates="task", cascade="all, delete-orphan")
    labels: Mapped[List["Label"]] = relationship("Label", secondary=task_labels, back_populates="tasks")
    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates="task", cascade="all, delete-orphan")
    attachments: Mapped[List["Attachment"]] = relationship("Attachment", back_populates="task", cascade="all, delete-orphan")


class Subtask(Base):
    """
    Checklist items embedded within a parent task.
    """

    __tablename__ = "subtasks"
    __table_args__ = (
        Index("idx_subtasks_task_order", "task_id", "order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        doc="Subtask primary key",
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        doc="Parent task foreign key",
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Checklist item text",
    )

    completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        doc="Completion check state",
    )

    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Sort order within checklist",
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
    task: Mapped["Task"] = relationship("Task", back_populates="subtasks")


class Label(Base):
    """
    Organization-scoped categorization tags.
    """

    __tablename__ = "labels"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_labels_org_name"),
        Index("idx_labels_org_id", "organization_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        doc="Label primary key",
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        doc="Tenant organization foreign key",
    )

    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Label tag name (e.g. 'Bug', 'Frontend')",
    )

    color: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="#8B7CFF",
        server_default="#8B7CFF",
        doc="Badge hex color code",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        doc="Creation timestamp",
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    tasks: Mapped[List["Task"]] = relationship("Task", secondary=task_labels, back_populates="labels")
