import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.security import decode_supabase_jwt
from app.dependencies.database import get_db
from app.models.enums import UserRole
from app.models.organization import Organization, OrganizationMember
from app.models.user import User

logger = logging.getLogger("flowstate.auth_dependencies")

# Bearer token extractor without auto_error so we can return consistent AppException responses
http_bearer = HTTPBearer(auto_error=False)

# Role hierarchy ranking for minimum-role authorization checks
ROLE_HIERARCHY: Dict[UserRole, int] = {
    UserRole.OWNER: 60,
    UserRole.ADMIN: 50,
    UserRole.MANAGER: 40,
    UserRole.DEVELOPER: 30,
    UserRole.DESIGNER: 20,
    UserRole.VIEWER: 10,
}


@dataclass
class ActiveOrganizationContext:
    """
    Validated multi-tenant execution context for authenticated requests.
    Guarantees that the authenticated user is an active member of the active organization.
    """

    organization: Organization
    member: OrganizationMember
    user: User
    role: UserRole

    @property
    def organization_id(self) -> uuid.UUID:
        return self.organization.id

    @property
    def user_id(self) -> uuid.UUID:
        return self.user.id

    def has_role(self, *roles: UserRole) -> bool:
        return self.role in roles

    def has_min_role(self, min_role: UserRole) -> bool:
        user_rank = ROLE_HIERARCHY.get(self.role, 0)
        min_rank = ROLE_HIERARCHY.get(min_role, 0)
        return user_rank >= min_rank


async def get_token_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
) -> Dict[str, Any]:
    """
    Extracts Bearer token from the Authorization header and verifies its cryptographic signature,
    expiration, audience, and claims.
    """
    if not credentials or not credentials.credentials:
        raise UnauthorizedException(
            "Authentication required. Missing Bearer token in Authorization header.",
            code="MISSING_TOKEN",
        )

    payload = decode_supabase_jwt(credentials.credentials)

    sub = payload.get("sub")
    if not sub:
        raise UnauthorizedException(
            "Invalid authentication token: missing 'sub' (subject) claim.",
            code="INVALID_TOKEN_SUBJECT",
        )

    try:
        uuid.UUID(str(sub))
    except (ValueError, TypeError) as e:
        raise UnauthorizedException(
            f"Invalid authentication token: subject '{sub}' is not a valid UUID.",
            code="INVALID_TOKEN_SUBJECT",
        ) from e

    return payload


async def get_current_user(
    token_payload: Dict[str, Any] = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolves the authenticated user's profile from the public.users database table.
    Ensures the account exists and is in active status.
    """
    user_id = uuid.UUID(str(token_payload["sub"]))

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedException(
            f"User profile '{user_id}' does not exist in application database.",
            code="USER_NOT_FOUND",
            details={"user_id": str(user_id)},
        )

    if not user.is_active:
        raise ForbiddenException(
            "User account has been deactivated. Please contact your workspace administrator.",
            code="USER_DEACTIVATED",
            details={"user_id": str(user_id)},
        )

    return user


async def get_active_organization(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ActiveOrganizationContext:
    """
    Resolves and cryptographically enforces the active tenant organization context.
    
    CRITICAL SECURITY INVARIANT (Requirement 8):
    Never trust an organization_id supplied by the frontend without verifying that the
    authenticated user has an explicit, active row in organization_members for that organization.
    
    Resolution order:
    1. Header: 'X-Organization-Id' or 'X-Workspace-Id'
    2. Query parameter: 'organization_id'
    3. Path parameter: 'organization_id'
    4. Fallback: User's default / primary organization (oldest membership)
    """
    # 1. Inspect potential client-provided organization identifiers
    raw_org_id = (
        request.headers.get("X-Organization-Id")
        or request.headers.get("X-Workspace-Id")
        or request.query_params.get("organization_id")
        or request.path_params.get("organization_id")
    )

    if raw_org_id and raw_org_id.strip():
        try:
            target_org_id = uuid.UUID(raw_org_id.strip())
        except (ValueError, TypeError) as e:
            raise BadRequestException(
                f"Invalid organization_id format: '{raw_org_id}'. Expected UUID.",
                code="INVALID_ORGANIZATION_ID",
                details={"provided_id": raw_org_id},
            ) from e

        # Query explicit membership
        stmt = (
            select(OrganizationMember, Organization)
            .join(Organization, Organization.id == OrganizationMember.organization_id)
            .where(
                OrganizationMember.organization_id == target_org_id,
                OrganizationMember.user_id == current_user.id,
            )
        )
        row = (await db.execute(stmt)).first()

        if not row:
            # Check if organization exists to return 404 vs 403
            org_exists = await db.scalar(select(Organization.id).where(Organization.id == target_org_id))
            if not org_exists:
                raise NotFoundException(
                    f"Organization '{target_org_id}' not found.",
                    code="ORGANIZATION_NOT_FOUND",
                    details={"organization_id": str(target_org_id)},
                )
            raise ForbiddenException(
                f"Access denied: You are not a member of organization '{target_org_id}'.",
                code="ORGANIZATION_ACCESS_DENIED",
                details={"organization_id": str(target_org_id)},
            )

        member, org = row
        return ActiveOrganizationContext(
            organization=org,
            member=member,
            user=current_user,
            role=member.role,
        )

    # 2. No explicit organization requested: resolve to default (first active membership)
    stmt = (
        select(OrganizationMember, Organization)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .where(OrganizationMember.user_id == current_user.id)
        .order_by(OrganizationMember.joined_at.asc())
        .limit(1)
    )
    default_row = (await db.execute(stmt)).first()

    if not default_row:
        raise ForbiddenException(
            "User does not belong to any organization. Please create or join an organization.",
            code="NO_ORGANIZATION_MEMBERSHIP",
            details={"user_id": str(current_user.id)},
        )

    member, org = default_row
    return ActiveOrganizationContext(
        organization=org,
        member=member,
        user=current_user,
        role=member.role,
    )


def require_org_role(*allowed_roles: UserRole):
    """
    Factory creating a dependency that strictly permits only specified organization roles.
    
    Usage:
        @router.post("/projects")
        async def create_project(
            ctx: ActiveOrganizationContext = Depends(require_org_role(UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER))
        ):
    """
    async def role_checker(
        context: ActiveOrganizationContext = Depends(get_active_organization),
    ) -> ActiveOrganizationContext:
        if context.role not in allowed_roles:
            allowed_names = [r.value for r in allowed_roles]
            raise ForbiddenException(
                f"Access denied: This operation requires one of the following roles: {allowed_names}. Your role in this organization is '{context.role.value}'.",
                code="INSUFFICIENT_ROLE_PERMISSIONS",
                details={
                    "required_roles": allowed_names,
                    "current_role": context.role.value,
                    "organization_id": str(context.organization.id),
                },
            )
        return context

    return role_checker


def require_min_org_role(min_role: UserRole):
    """
    Factory creating a dependency that requires a minimum hierarchical organization role.
    Role hierarchy: OWNER (60) > ADMIN (50) > MANAGER (40) > DEVELOPER (30) > DESIGNER (20) > VIEWER (10).
    """
    async def min_role_checker(
        context: ActiveOrganizationContext = Depends(get_active_organization),
    ) -> ActiveOrganizationContext:
        if not context.has_min_role(min_role):
            raise ForbiddenException(
                f"Access denied: This operation requires minimum role '{min_role.value}'. Your role in this organization is '{context.role.value}'.",
                code="INSUFFICIENT_ROLE_PERMISSIONS",
                details={
                    "min_required_role": min_role.value,
                    "current_role": context.role.value,
                    "organization_id": str(context.organization.id),
                },
            )
        return context

    return min_role_checker
