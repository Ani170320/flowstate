import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base

if TYPE_CHECKING:
    from app.models.organization import OrganizationMember

# External schema stub referencing Supabase's managed auth.users table.
# Informs SQLAlchemy's MetaData of auth.users.id so foreign keys resolve cleanly
# without attempting to manage or recreate Supabase's internal auth schema.
Table(
    "users",
    Base.metadata,
    Column("id", Uuid, primary_key=True),
    schema="auth",
)


class User(Base):
    """
    Application profile model for registered users.
    1:1 relationship with Supabase auth.users table.
    """

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email_lower", text("lower(email)"), unique=True),
    )

    # Primary key directly maps to Supabase auth.users(id)
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        primary_key=True,
        doc="Direct 1:1 foreign key reference to Supabase auth.users(id)",
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="User email address synchronized from auth.users (case-insensitive unique)",
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        doc="User display name",
    )

    avatar_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Public CDN / Supabase Storage avatar image URL",
    )

    department: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Department within organization (e.g., Engineering, Design)",
    )

    title: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Job title (e.g., Staff Frontend Engineer)",
    )

    phone: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        doc="Optional contact phone number",
    )

    bio: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Short user profile biography",
    )

    timezone: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="UTC",
        server_default="UTC",
        doc="User preferred IANA timezone",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        doc="Soft account status flag",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        doc="Profile creation timestamp",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Profile last update timestamp",
    )

    # Relationships
    organization_memberships: Mapped[List["OrganizationMember"]] = relationship(
        "OrganizationMember",
        back_populates="user",
        cascade="all, delete-orphan",
        doc="Organizations this user belongs to",
    )
