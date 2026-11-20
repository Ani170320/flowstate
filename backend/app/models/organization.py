import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    JSON,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base
from app.models.enums import SubscriptionPlan, UserRole

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.team import Team
    from app.models.user import User


class Organization(Base):
    """
    Tenant root entity representing an organization, company, or team workspace.
    """

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        doc="Organization primary key",
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        doc="Display name of the organization",
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="URL-friendly unique slug (e.g. 'flowstate-labs')",
    )

    logo_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Public storage URL for organization logo",
    )

    plan: Mapped[SubscriptionPlan] = mapped_column(
        SQLEnum(
            SubscriptionPlan,
            name="subscription_plan",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=SubscriptionPlan.FREE,
        server_default="free",
        doc="SaaS subscription tier",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        doc="Timestamp when organization was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Timestamp when organization was last updated",
    )

    # Relationships
    members: Mapped[List["OrganizationMember"]] = relationship(
        "OrganizationMember",
        back_populates="organization",
        cascade="all, delete-orphan",
        doc="Members enrolled in this organization",
    )

    settings: Mapped[Optional["WorkspaceSettings"]] = relationship(
        "WorkspaceSettings",
        back_populates="organization",
        uselist=False,
        cascade="all, delete-orphan",
        doc="Tenant workspace settings (1:1)",
    )

    teams: Mapped[List["Team"]] = relationship(
        "Team",
        back_populates="organization",
        cascade="all, delete-orphan",
        doc="Teams belonging to this organization",
    )

    projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="organization",
        cascade="all, delete-orphan",
        doc="Projects belonging to this organization",
    )


class OrganizationMember(Base):
    """
    Junction entity representing user membership and RBAC role inside an organization.
    """

    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_organization_members_org_user"),
        Index("idx_org_members_user_id", "user_id"),
        Index("idx_org_members_org_role", "organization_id", "role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        doc="Membership record identifier",
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        doc="Associated organization identifier",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Associated user profile identifier",
    )

    role: Mapped[UserRole] = mapped_column(
        SQLEnum(
            UserRole,
            name="user_role",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=UserRole.DEVELOPER,
        server_default="developer",
        doc="Role within organization (RBAC)",
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        doc="Timestamp when member joined organization",
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="organization_memberships")


class WorkspaceSettings(Base):
    """
    1:1 organization-level workspace preferences and defaults.
    """

    __tablename__ = "workspace_settings"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_workspace_settings_org_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        doc="Settings record identifier",
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        doc="Associated organization identifier (1:1)",
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="USD",
        server_default="USD",
        doc="Workspace billing/financial currency code",
    )

    timezone: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="America/San_Francisco",
        server_default="America/San_Francisco",
        doc="Workspace default IANA timezone",
    )

    working_days: Mapped[List[int]] = mapped_column(
        ARRAY(SmallInteger).with_variant(JSON, "sqlite"),
        nullable=False,
        default=lambda: [1, 2, 3, 4, 5],
        server_default="{1,2,3,4,5}",
        doc="Working days array: 1=Mon .. 7=Sun",
    )

    notifications_email: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        doc="Default email notification dispatch",
    )

    notifications_desktop: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        doc="Default desktop push notification dispatch",
    )

    theme: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="dark",
        server_default="dark",
        doc="Workspace UI theme: 'dark', 'midnight', 'system'",
    )

    accent_color: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="#8B7CFF",
        server_default="#8B7CFF",
        doc="Primary workspace UI accent color hex",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Settings last update timestamp",
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="settings")
