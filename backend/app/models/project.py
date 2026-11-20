import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base
from app.models.enums import PriorityLevel, ProjectStatus

if TYPE_CHECKING:
    from app.models.collaboration import Activity, Attachment
    from app.models.organization import Organization
    from app.models.task import Task
    from app.models.team import Team
    from app.models.user import User


class Project(Base):
    """
    Project containers tracking status, priority, budgets, and sequential task keys.
    """

    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("id", "organization_id", name="uq_projects_id_org"),
        UniqueConstraint("organization_id", "key", name="uq_projects_org_key"),
        CheckConstraint("progress >= 0 AND progress <= 100", name="chk_projects_progress"),
        Index("idx_projects_org_status", "organization_id", "status"),
        Index("idx_projects_team_id", "team_id"),
        Index("idx_projects_manager_id", "manager_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        doc="Project primary key",
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        doc="Tenant organization foreign key",
    )

    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        doc="Optional team owning this project",
    )

    key: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        doc="Short uppercase key prefix for project tasks (e.g. 'FLW', 'DS')",
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Project title",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Project description and scope",
    )

    status: Mapped[ProjectStatus] = mapped_column(
        SQLEnum(
            ProjectStatus,
            name="project_status",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=ProjectStatus.PLANNING,
        server_default="planning",
        doc="Current lifecycle state",
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
        doc="Project urgency ranking",
    )

    color: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="#8B7CFF",
        server_default="#8B7CFF",
        doc="Accent badge hex color code",
    )

    start_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="Planned project start date",
    )

    due_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="Project deadline date",
    )

    manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Assigned project manager",
    )

    progress: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default="0",
        doc="Completion percentage (0 to 100)",
    )

    budget: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2),
        nullable=True,
        default=Decimal("0.00"),
        server_default="0.00",
        doc="Total allocated budget",
    )

    spent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2),
        nullable=True,
        default=Decimal("0.00"),
        server_default="0.00",
        doc="Actual costs incurred",
    )

    last_task_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        server_default="100",
        doc="Atomic sequence counter for sequential task keys",
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
    organization: Mapped["Organization"] = relationship("Organization", back_populates="projects")
    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="projects")
    manager: Mapped[Optional["User"]] = relationship("User", foreign_keys=[manager_id])
    members: Mapped[List["ProjectMember"]] = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    attachments: Mapped[List["Attachment"]] = relationship("Attachment", back_populates="project")
    activities: Mapped[List["Activity"]] = relationship("Activity", back_populates="project")


class ProjectMember(Base):
    """
    Explicit user participation in projects.
    """

    __tablename__ = "project_members"
    __table_args__ = (
        Index("idx_project_members_user_id", "user_id"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
        doc="Project foreign key",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        doc="User foreign key",
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        doc="Assignment timestamp",
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="members")
    user: Mapped["User"] = relationship("User")
