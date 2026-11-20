import json
import logging
import re
import uuid
from typing import Any, List, Optional, Union

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.models.enums import SubscriptionPlan, UserRole
from app.models.organization import Organization, OrganizationMember, WorkspaceSettings
from app.models.user import User
from app.schemas.organization import (
    AddMemberRequest,
    OrganizationBillingPlanUpdateRequest,
    OrganizationCreateRequest,
    OrganizationDetailResponse,
    OrganizationMemberResponse,
    OrganizationUpdateRequest,
    UpdateMemberRoleRequest,
    WorkspaceSettingsResponse,
    WorkspaceSettingsUpdateRequest,
)

logger = logging.getLogger("flowstate.routes.organizations")

router = APIRouter(prefix="/organizations", tags=["Organizations & Workspace"])


def slugify(text: str) -> str:
    """Generates an ASCII-lowercase URL-friendly slug from text."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return re.sub(r"^-+|-+$", "", text)


DEFAULT_ORG_UUID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def resolve_org_uuid(org_id_val: Union[uuid.UUID, str]) -> uuid.UUID:
    if isinstance(org_id_val, uuid.UUID):
        return org_id_val
    s = str(org_id_val).lower().strip()
    if s in ("org_default", "default", "default-org"):
        return DEFAULT_ORG_UUID
    try:
        return uuid.UUID(s)
    except ValueError:
        raise NotFoundException(f"Organization '{org_id_val}' not found.", code="ORGANIZATION_NOT_FOUND")


async def get_org_membership(
    org_id: Union[uuid.UUID, str],
    user_id: uuid.UUID,
    db: AsyncSession,
) -> tuple[Organization, OrganizationMember]:
    """
    Helper verifying that an organization exists and the user is an active member.
    Raises NotFoundException (404) or ForbiddenException (403).
    """
    resolved_id = resolve_org_uuid(org_id)
    stmt = (
        select(OrganizationMember, Organization)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .options(selectinload(Organization.settings))
        .where(
            OrganizationMember.organization_id == resolved_id,
            OrganizationMember.user_id == user_id,
        )
    )
    row = (await db.execute(stmt)).first()

    if not row:
        org_exists = await db.scalar(select(Organization.id).where(Organization.id == resolved_id))
        if not org_exists:
            raise NotFoundException(f"Organization '{org_id}' not found.", code="ORGANIZATION_NOT_FOUND")
        raise ForbiddenException(
            f"Access denied: You are not a member of organization '{org_id}'.",
            code="ORGANIZATION_ACCESS_DENIED",
        )

    member, org = row
    return org, member


# ---------------------------------------------------------------------------
# 1. Organization Management
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=OrganizationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Organization",
    description="Creates a new tenant organization, initializes default workspace settings, and enlists creator as Owner.",
)
async def create_organization(
    payload: OrganizationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationDetailResponse:
    # 0. Subscription Security: Reject client attempts to self-assign paid plans on creation
    if payload.plan is not None and payload.plan != SubscriptionPlan.FREE:
        raise BadRequestException(
            f"New organizations cannot self-assign paid plan '{payload.plan.value}'. All workspaces must start on the free tier. Upgrades must be initiated via the billing checkout flow.",
            code="UNAUTHORIZED_PAID_PLAN_ASSIGNMENT",
        )

    # 1. Generate or validate slug
    base_slug = payload.slug.strip().lower() if payload.slug and payload.slug.strip() else slugify(payload.name)
    if not base_slug:
        base_slug = f"org-{uuid.uuid4().hex[:8]}"

    # Check for slug collision and ensure uniqueness
    existing_slug = await db.scalar(select(Organization.id).where(Organization.slug == base_slug))
    if existing_slug:
        if payload.slug:
            raise BadRequestException(
                f"Slug '{payload.slug}' is already in use. Please select a different slug.",
                code="SLUG_COLLISION",
            )
        base_slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

    # 2. Create Organization record - strictly enforce SubscriptionPlan.FREE
    new_org = Organization(
        name=payload.name.strip(),
        slug=base_slug,
        logo_url=payload.logo_url.strip() if payload.logo_url else None,
        plan=SubscriptionPlan.FREE,
    )
    db.add(new_org)
    await db.flush()

    # 3. Create default WorkspaceSettings record
    default_settings = WorkspaceSettings(
        organization_id=new_org.id,
        currency="USD",
        timezone="UTC",
        working_days=[1, 2, 3, 4, 5],
        notifications_email=True,
        notifications_desktop=True,
        theme="dark",
        accent_color="#8B7CFF",
    )
    db.add(default_settings)

    # 4. Enlist creator as Organization OWNER
    membership = OrganizationMember(
        organization_id=new_org.id,
        user_id=current_user.id,
        role=UserRole.OWNER,
    )
    db.add(membership)
    await db.commit()
    await db.refresh(new_org)
    await db.refresh(default_settings)

    return OrganizationDetailResponse(
        id=new_org.id,
        name=new_org.name,
        slug=new_org.slug,
        logo_url=new_org.logo_url,
        plan=new_org.plan,
        current_user_role=UserRole.OWNER,
        members_count=1,
        settings=WorkspaceSettingsResponse.model_validate(default_settings),
        created_at=new_org.created_at,
        updated_at=new_org.updated_at,
    )


@router.get(
    "",
    response_model=List[OrganizationDetailResponse],
    summary="List Organizations",
    description="Retrieves all tenant organizations where the authenticated user is an enrolled member.",
)
async def list_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[OrganizationDetailResponse]:
    # Query organizations where current user has a membership record
    stmt = (
        select(Organization, OrganizationMember.role)
        .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
        .options(selectinload(Organization.settings))
        .where(OrganizationMember.user_id == current_user.id)
        .order_by(Organization.name.asc())
    )
    rows = (await db.execute(stmt)).all()

    results: List[OrganizationDetailResponse] = []
    for org, user_role in rows:
        # Get count of members for this org
        members_count = await db.scalar(
            select(func.count(OrganizationMember.id)).where(OrganizationMember.organization_id == org.id)
        ) or 1

        results.append(
            OrganizationDetailResponse(
                id=org.id,
                name=org.name,
                slug=org.slug,
                logo_url=org.logo_url,
                plan=org.plan,
                current_user_role=user_role,
                members_count=members_count,
                settings=WorkspaceSettingsResponse.model_validate(org.settings) if org.settings else None,
                created_at=org.created_at,
                updated_at=org.updated_at,
            )
        )

    return results


@router.get(
    "/{organization_id}",
    response_model=OrganizationDetailResponse,
    summary="Get Organization Details",
    description="Retrieves comprehensive details of a specific organization if user has verified membership.",
)
async def get_organization_details(
    organization_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationDetailResponse:
    org, member = await get_org_membership(organization_id, current_user.id, db)

    members_count = await db.scalar(
        select(func.count(OrganizationMember.id)).where(OrganizationMember.organization_id == org.id)
    ) or 1

    return OrganizationDetailResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        logo_url=org.logo_url,
        plan=org.plan,
        current_user_role=member.role,
        members_count=members_count,
        settings=WorkspaceSettingsResponse.model_validate(org.settings) if org.settings else None,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


@router.patch(
    "/{organization_id}",
    response_model=OrganizationDetailResponse,
    summary="Update Organization",
    description="Modifies organization name, slug, logo, or subscription plan. Requires OWNER or ADMIN role.",
)
async def update_organization(
    organization_id: uuid.UUID,
    payload: OrganizationUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationDetailResponse:
    org, member = await get_org_membership(organization_id, current_user.id, db)

    # Permission check: Only OWNER or ADMIN can modify organization profile
    if member.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise ForbiddenException(
            f"Permission denied: Modifying organization details requires Owner or Admin role. Your role is '{member.role.value}'.",
            code="INSUFFICIENT_ROLE_PERMISSIONS",
        )

    # Validate slug uniqueness if changed
    if payload.slug is not None:
        target_slug = payload.slug.strip().lower()
        if target_slug != org.slug:
            existing = await db.scalar(
                select(Organization.id).where(Organization.slug == target_slug, Organization.id != org.id)
            )
            if existing:
                raise BadRequestException(f"Slug '{target_slug}' is already taken.", code="SLUG_COLLISION")
            org.slug = target_slug

    # 0. Subscription Security: Clients cannot update subscription plans via standard PATCH
    if payload.plan is not None:
        raise ForbiddenException(
            "Subscription plans cannot be modified via standard organization updates. Plan changes are strictly managed by server-side billing processes.",
            code="PLAN_UPDATE_RESTRICTED",
        )

    current_role = member.role
    if payload.name is not None:
        org.name = payload.name.strip()
    if payload.logo_url is not None:
        org.logo_url = payload.logo_url.strip() if payload.logo_url.strip() else None

    await db.commit()
    await db.refresh(org)

    settings = await db.scalar(
        select(WorkspaceSettings).where(WorkspaceSettings.organization_id == org.id)
    )

    members_count = await db.scalar(
        select(func.count(OrganizationMember.id)).where(OrganizationMember.organization_id == org.id)
    ) or 1

    return OrganizationDetailResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        logo_url=org.logo_url,
        plan=org.plan,
        current_user_role=current_role,
        members_count=members_count,
        settings=WorkspaceSettingsResponse.model_validate(settings) if settings else None,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


@router.post(
    "/{organization_id}/billing/plan",
    response_model=OrganizationDetailResponse,
    summary="Update Subscription Plan (Trusted Billing Process)",
    description="Administrative endpoint callable only by server-side billing webhooks/processes with a valid X-Billing-Secret.",
)
async def update_organization_plan_billing(
    organization_id: uuid.UUID,
    payload: OrganizationBillingPlanUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> OrganizationDetailResponse:
    secret_header = request.headers.get("X-Billing-Secret") or request.headers.get("x-billing-secret")
    expected_secret = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SECRET_KEY
    if not secret_header or secret_header != expected_secret:
        raise ForbiddenException(
            "Access denied: Invalid or missing billing process credentials.",
            code="INVALID_BILLING_CREDENTIALS",
        )

    org = await db.scalar(select(Organization).where(Organization.id == organization_id))
    if not org:
        raise NotFoundException(f"Organization '{organization_id}' not found.", code="ORGANIZATION_NOT_FOUND")

    org.plan = payload.plan
    await db.commit()
    await db.refresh(org)

    settings_obj = await db.scalar(
        select(WorkspaceSettings).where(WorkspaceSettings.organization_id == org.id)
    )
    members_count = await db.scalar(
        select(func.count(OrganizationMember.id)).where(OrganizationMember.organization_id == org.id)
    ) or 1

    return OrganizationDetailResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        logo_url=org.logo_url,
        plan=org.plan,
        current_user_role=UserRole.OWNER,
        members_count=members_count,
        settings=WorkspaceSettingsResponse.model_validate(settings_obj) if settings_obj else None,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


# ---------------------------------------------------------------------------
# 2. Member Management
# ---------------------------------------------------------------------------

@router.get(
    "/{organization_id}/members",
    response_model=List[OrganizationMemberResponse],
    summary="List Organization Members",
    description="Returns all enrolled members of the organization with user profiles. Requires membership.",
)
async def list_organization_members(
    organization_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[OrganizationMemberResponse]:
    # Ensure caller is a member
    await get_org_membership(organization_id, current_user.id, db)

    stmt = (
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.user))
        .where(OrganizationMember.organization_id == organization_id)
        .order_by(OrganizationMember.joined_at.asc())
    )
    members = (await db.execute(stmt)).scalars().all()

    return [
        OrganizationMemberResponse(
            id=m.id,
            organization_id=m.organization_id,
            user_id=m.user_id,
            role=m.role,
            joined_at=m.joined_at,
            user=m.user,
        )
        for m in members
    ]


@router.post(
    "/{organization_id}/members",
    response_model=OrganizationMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Organization Member",
    description="Enrolls an existing user into the organization. Requires OWNER or ADMIN role.",
)
async def add_organization_member(
    organization_id: uuid.UUID,
    payload: AddMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationMemberResponse:
    org, caller_member = await get_org_membership(organization_id, current_user.id, db)

    # 1. Authorization check
    if caller_member.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise ForbiddenException(
            "Access denied: Adding members requires Owner or Admin privileges.",
            code="INSUFFICIENT_ROLE_PERMISSIONS",
        )

    # 2. Admin role restrictions: Admins cannot grant Owner role
    if caller_member.role == UserRole.ADMIN and payload.role == UserRole.OWNER:
        raise ForbiddenException(
            "Admins cannot assign the Owner role. Only Owners can assign Owner privileges.",
            code="CANNOT_ASSIGN_OWNER_ROLE",
        )

    # 3. Locate target user
    target_user: Optional[User] = None
    if payload.user_id:
        target_user = await db.scalar(select(User).where(User.id == payload.user_id))
    elif payload.email and payload.email.strip():
        email_clean = payload.email.strip().lower()
        target_user = await db.scalar(select(User).where(func.lower(User.email) == email_clean))
    else:
        raise BadRequestException("Either 'email' or 'user_id' must be provided to add a member.", code="MISSING_TARGET_USER")

    if not target_user:
        if payload.email and payload.email.strip():
            clean_email = payload.email.strip().lower()
            new_user_id = uuid.uuid4()
            disp_name = (payload.name or "").strip() or clean_email.split("@")[0].capitalize()
            # 1. Insert into auth.users (satisfying foreign key public.users.id -> auth.users.id)
            await db.execute(
                text(
                    """
                    INSERT INTO auth.users (id, email, raw_user_meta_data, created_at, updated_at, aud, role)
                    VALUES (:id, :email, CAST(:meta AS jsonb), NOW(), NOW(), 'authenticated', 'authenticated')
                    ON CONFLICT (id) DO NOTHING;
                    """
                ),
                {
                    "id": new_user_id,
                    "email": clean_email,
                    "meta": json.dumps({"full_name": disp_name, "name": disp_name}),
                },
            )
            # 2. Check if trigger populated public.users; if not, create explicitly
            target_user = await db.scalar(select(User).where(User.id == new_user_id))
            if not target_user:
                target_user = User(
                    id=new_user_id,
                    email=clean_email,
                    name=disp_name,
                    department=payload.department or "Engineering",
                    title=payload.title or "Team Member",
                    avatar_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed={clean_email}",
                    is_active=True,
                )
                db.add(target_user)
                await db.flush()
            else:
                if payload.department:
                    target_user.department = payload.department
                if payload.title:
                    target_user.title = payload.title
        else:
            identifier = payload.email or str(payload.user_id)
            raise NotFoundException(
                f"User '{identifier}' does not exist in FLOWSTATE. They must create an account first.",
                code="USER_NOT_FOUND",
            )

    # 4. Check for duplicate membership
    existing_mem = await db.scalar(
        select(OrganizationMember.id).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == target_user.id,
        )
    )
    if existing_mem:
        raise BadRequestException(
            f"User '{target_user.email}' is already an enrolled member of this organization.",
            code="MEMBER_ALREADY_EXISTS",
        )

    # 5. Insert membership record
    new_member = OrganizationMember(
        organization_id=organization_id,
        user_id=target_user.id,
        role=payload.role,
    )
    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)

    return OrganizationMemberResponse(
        id=new_member.id,
        organization_id=new_member.organization_id,
        user_id=new_member.user_id,
        role=new_member.role,
        joined_at=new_member.joined_at,
        user=target_user,
    )


@router.patch(
    "/{organization_id}/members/{user_id}",
    response_model=OrganizationMemberResponse,
    summary="Update Member Role",
    description="Updates a member's RBAC role within the organization. Requires OWNER or ADMIN role.",
)
async def update_member_role(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: UpdateMemberRoleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrganizationMemberResponse:
    org, caller = await get_org_membership(organization_id, current_user.id, db)

    # 1. Caller permissions
    if caller.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise ForbiddenException("Permission denied: Modifying member roles requires Owner or Admin privileges.", code="INSUFFICIENT_ROLE_PERMISSIONS")

    # 2. Retrieve target member
    stmt = (
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.user))
        .where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    )
    target_member = (await db.execute(stmt)).scalar_one_or_none()

    if not target_member:
        raise NotFoundException(f"Member '{user_id}' not found in this organization.", code="MEMBER_NOT_FOUND")

    # 3. RBAC Guards:
    # - Admins cannot alter an Owner's role
    if caller.role == UserRole.ADMIN and target_member.role == UserRole.OWNER:
        raise ForbiddenException("Admins cannot modify an Owner's role.", code="CANNOT_MODIFY_OWNER")

    # - Admins cannot promote anyone to Owner
    if caller.role == UserRole.ADMIN and payload.role == UserRole.OWNER:
        raise ForbiddenException("Admins cannot promote members to Owner.", code="CANNOT_PROMOTE_TO_OWNER")

    # - Sole Owner protection: If Owner is demoting themselves, ensure another Owner exists
    if target_member.role == UserRole.OWNER and payload.role != UserRole.OWNER:
        owners_count = await db.scalar(
            select(func.count(OrganizationMember.id)).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.role == UserRole.OWNER,
            )
        ) or 1
        if owners_count <= 1:
            raise BadRequestException(
                "Cannot demote the sole organization Owner. Designate another Owner before changing role.",
                code="SOLE_OWNER_DEMOTION_FORBIDDEN",
            )

    target_user = target_member.user
    target_member.role = payload.role
    await db.commit()
    await db.refresh(target_member)

    return OrganizationMemberResponse(
        id=target_member.id,
        organization_id=target_member.organization_id,
        user_id=target_member.user_id,
        role=target_member.role,
        joined_at=target_member.joined_at,
        user=target_user,
    )


@router.delete(
    "/{organization_id}/members/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove Organization Member",
    description="Expels a user from the organization. Members can remove themselves (leave), while Owners and Admins can expel others.",
)
async def remove_organization_member(
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    org, caller = await get_org_membership(organization_id, current_user.id, db)

    stmt = select(OrganizationMember).where(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == user_id,
    )
    target_member = (await db.execute(stmt)).scalar_one_or_none()

    if not target_member:
        raise NotFoundException(f"Member '{user_id}' not found in this organization.", code="MEMBER_NOT_FOUND")

    # 1. Self-removal (leaving the organization)
    if caller.user_id == target_member.user_id:
        if target_member.role == UserRole.OWNER:
            owners_count = await db.scalar(
                select(func.count(OrganizationMember.id)).where(
                    OrganizationMember.organization_id == organization_id,
                    OrganizationMember.role == UserRole.OWNER,
                )
            ) or 1
            if owners_count <= 1:
                raise BadRequestException(
                    "The sole organization Owner cannot leave. Transfer ownership or delete the organization.",
                    code="SOLE_OWNER_LEAVE_FORBIDDEN",
                )
    else:
        # 2. Removing someone else
        if caller.role not in [UserRole.OWNER, UserRole.ADMIN]:
            raise ForbiddenException("Permission denied: Only Owners and Admins can remove other members.", code="INSUFFICIENT_ROLE_PERMISSIONS")

        if caller.role == UserRole.ADMIN and target_member.role in [UserRole.OWNER, UserRole.ADMIN]:
            raise ForbiddenException("Admins cannot remove Owners or fellow Admins.", code="CANNOT_REMOVE_PRIVILEGED_MEMBER")

    await db.delete(target_member)
    await db.commit()

    return {
        "status": "success",
        "message": f"User '{user_id}' successfully removed from organization '{org.name}'.",
        "organization_id": str(organization_id),
        "user_id": str(user_id),
    }


# ---------------------------------------------------------------------------
# 3. Workspace Settings
# ---------------------------------------------------------------------------

@router.get(
    "/{organization_id}/settings",
    response_model=WorkspaceSettingsResponse,
    summary="Get Workspace Settings",
    description="Retrieves configuration preferences for an organization workspace. Requires membership.",
)
async def get_workspace_settings(
    organization_id: Union[uuid.UUID, str],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceSettingsResponse:
    target_id = resolve_org_uuid(organization_id)
    org, _ = await get_org_membership(target_id, current_user.id, db)

    settings = await db.scalar(
        select(WorkspaceSettings).where(WorkspaceSettings.organization_id == target_id)
    )
    if not settings:
        # Fallback creation if settings row was missing
        settings = WorkspaceSettings(organization_id=target_id)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return WorkspaceSettingsResponse.model_validate(settings)


@router.patch(
    "/{organization_id}/settings",
    response_model=WorkspaceSettingsResponse,
    summary="Update Workspace Settings",
    description="Updates workspace currency, timezone, working days, themes, or notification preferences. Requires OWNER or ADMIN.",
)
async def update_workspace_settings(
    organization_id: Union[uuid.UUID, str],
    payload: WorkspaceSettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceSettingsResponse:
    target_id = resolve_org_uuid(organization_id)
    org, member = await get_org_membership(target_id, current_user.id, db)

    # Permission check: Only OWNER or ADMIN can modify workspace configuration
    if member.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise ForbiddenException(
            "Access denied: Modifying workspace settings requires Owner or Admin privileges.",
            code="INSUFFICIENT_ROLE_PERMISSIONS",
        )

    settings = await db.scalar(
        select(WorkspaceSettings).where(WorkspaceSettings.organization_id == target_id)
    )
    if not settings:
        settings = WorkspaceSettings(organization_id=target_id)
        db.add(settings)
        await db.flush()

    if payload.currency is not None:
        settings.currency = payload.currency.upper()
    if payload.timezone is not None:
        settings.timezone = payload.timezone.strip()
    if payload.working_days is not None:
        settings.working_days = payload.working_days
    if payload.notifications_email is not None:
        settings.notifications_email = payload.notifications_email
    if payload.notifications_desktop is not None:
        settings.notifications_desktop = payload.notifications_desktop
    if payload.theme is not None:
        settings.theme = payload.theme.strip()
    if payload.accent_color is not None:
        settings.accent_color = payload.accent_color.strip()

    await db.commit()
    await db.refresh(settings)

    return WorkspaceSettingsResponse.model_validate(settings)
