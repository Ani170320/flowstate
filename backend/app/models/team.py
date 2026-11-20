import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.project import Project
    from app.models.user import User


class Team(Base):
    """
    Functional team units within an organization (e.g. Engineering, Design, Marketing).
    """

    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("id", "organization_id", name="uq_teams_id_org"),
        UniqueConstraint("organization_id", "name", name="uq_teams_org_name"),
        Index("idx_teams_org_id", "organization_id"),
        Index("idx_teams_lead_id", "lead_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        doc="Team primary key",
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        doc="Tenant organization foreign key",
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        doc="Team name",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Optional team description or charter",
    )

    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Team lead user reference",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        doc="Team creation timestamp",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Team last update timestamp",
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="teams")
    lead: Mapped[Optional["User"]] = relationship("User", foreign_keys=[lead_id])
    members: Mapped[List["TeamMember"]] = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="team")


class TeamMember(Base):
    """
    Junction table mapping users to teams.
    """

    __tablename__ = "team_members"
    __table_args__ = (
        Index("idx_team_members_user_id", "user_id"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("teams.id", ondelete="CASCADE"),
        primary_key=True,
        doc="Team foreign key",
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
        doc="Membership join timestamp",
    )

    # Relationships
    team: Mapped["Team"] = relationship("Team", back_populates="members")
    user: Mapped["User"] = relationship("User")
