import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Header, Query, Request, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException, UnauthorizedException
from app.core.security import create_jwt_token
from app.dependencies.auth import (
    ActiveOrganizationContext,
    get_active_organization,
    get_current_user,
    get_token_payload,
    require_min_org_role,
    require_org_role,
)
from app.dependencies.database import get_db
from app.models.enums import SubscriptionPlan, UserRole
from app.models.organization import Organization, OrganizationMember, WorkspaceSettings
from app.models.user import User
from app.schemas.auth import (
    ActiveOrganizationDetailResponse,
    AuthMeResponse,
    AuthSessionResponse,
    DemoSessionRequest,
    LoginRequest,
    OrganizationMembershipResponse,
    SignupRequest,
    SwitchOrganizationRequest,
    SwitchOrganizationResponse,
    TokenVerificationResponse,
    UpdateProfileRequest,
    UserProfileResponse,
)

logger = logging.getLogger("flowstate.routes.auth")

router = APIRouter(prefix="/auth", tags=["Authentication & Multi-Tenancy"])


@router.get(
    "/verify-token",
    response_model=TokenVerificationResponse,
    summary="Verify JWT Token",
    description="Validates token signature and expiration, returning subject claims.",
)
async def verify_token(
    payload: Dict[str, Any] = Depends(get_token_payload),
) -> TokenVerificationResponse:
    """Verifies the caller's JWT token and returns token metadata."""
    exp_timestamp = payload.get("exp", 0)
    expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)

    return TokenVerificationResponse(
        valid=True,
        user_id=uuid.UUID(str(payload["sub"])),
        email=payload.get("email"),
        auth_role=payload.get("role", "authenticated"),
        expires_at=expires_at,
    )


@router.get(
    "/me",
    response_model=AuthMeResponse,
    summary="Get Current User Session",
    description="Returns authenticated user profile, resolved active organization, and tenant memberships.",
)
async def get_my_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
) -> AuthMeResponse:
    logger.info(f"==> get_my_session: user={current_user.email}, name='{current_user.name}'")
    # 1. Fetch all memberships with their organization details
    stmt = (
        select(OrganizationMember, Organization)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .where(OrganizationMember.user_id == current_user.id)
        .order_by(OrganizationMember.joined_at.asc())
    )
    rows = (await db.execute(stmt)).all()

    organizations_list: List[OrganizationMembershipResponse] = []
    active_org_detail: ActiveOrganizationDetailResponse | None = None

    # Determine requested organization if specified in headers or params
    raw_requested_org = (
        request.headers.get("X-Organization-Id")
        or request.headers.get("X-Workspace-Id")
        or request.query_params.get("organization_id")
    ) if request else None

    target_org_uuid = None
    if raw_requested_org and raw_requested_org.strip():
        try:
            target_org_uuid = uuid.UUID(raw_requested_org.strip())
        except (ValueError, TypeError):
            pass

    for member, org in rows:
        membership_dto = OrganizationMembershipResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            logo_url=org.logo_url,
            plan=org.plan,
            role=member.role,
            joined_at=member.joined_at,
        )
        organizations_list.append(membership_dto)

        # Match active organization: either requested UUID or first membership
        if target_org_uuid and org.id == target_org_uuid:
            active_org_detail = ActiveOrganizationDetailResponse(
                id=org.id,
                name=org.name,
                slug=org.slug,
                logo_url=org.logo_url,
                plan=org.plan,
                role=member.role,
                joined_at=member.joined_at,
            )
        elif not target_org_uuid and active_org_detail is None:
            active_org_detail = ActiveOrganizationDetailResponse(
                id=org.id,
                name=org.name,
                slug=org.slug,
                logo_url=org.logo_url,
                plan=org.plan,
                role=member.role,
                joined_at=member.joined_at,
            )

    return AuthMeResponse(
        user=UserProfileResponse.model_validate(current_user),
        active_organization=active_org_detail,
        organizations=organizations_list,
    )


@router.patch(
    "/me",
    response_model=UserProfileResponse,
    summary="Update Current User Profile",
    description="Updates authenticated user profile details including name, email, phone number, bio, title, department, timezone, and avatar.",
)
async def update_my_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    if payload.name is not None and payload.name.strip():
        current_user.name = payload.name.strip()
        try:
            await db.execute(
                text("UPDATE auth.users SET raw_user_meta_data = jsonb_set(COALESCE(raw_user_meta_data, '{}'::jsonb), '{full_name}', :name_json) WHERE id = :id"),
                {"name_json": json.dumps(current_user.name), "id": current_user.id},
            )
        except Exception as meta_err:
            logger.warning(f"Could not update auth.users meta for {current_user.id}: {meta_err}")

    if payload.email is not None and payload.email.strip():
        clean_email = payload.email.strip().lower()
        if clean_email != current_user.email.lower():
            existing = await db.scalar(
                select(User.id).where(func.lower(User.email) == clean_email, User.id != current_user.id)
            )
            if existing:
                raise BadRequestException("This email is already in use by another account.", code="EMAIL_IN_USE")
            current_user.email = clean_email
            try:
                await db.execute(
                    text("UPDATE auth.users SET email = :email WHERE id = :id"),
                    {"email": clean_email, "id": current_user.id},
                )
            except Exception as auth_err:
                logger.warning(f"Could not update auth.users email for {current_user.id}: {auth_err}")

    if payload.title is not None:
        current_user.title = payload.title.strip() if payload.title.strip() else None
    if payload.department is not None:
        current_user.department = payload.department.strip() if payload.department.strip() else None
    if payload.phone is not None:
        current_user.phone = payload.phone.strip() if payload.phone.strip() else None
    if payload.bio is not None:
        current_user.bio = payload.bio.strip() if payload.bio.strip() else None
    if payload.timezone is not None and payload.timezone.strip():
        current_user.timezone = payload.timezone.strip()
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url.strip() if payload.avatar_url.strip() else None

    current_user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(current_user)
    return UserProfileResponse.model_validate(current_user)


@router.get(
    "/organizations",
    response_model=List[OrganizationMembershipResponse],
    summary="List User Organizations",
    description="Returns all tenant organizations the authenticated user belongs to.",
)
async def list_user_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[OrganizationMembershipResponse]:
    """Retrieves all organizations where the authenticated user is a verified member."""
    stmt = (
        select(OrganizationMember, Organization)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .where(OrganizationMember.user_id == current_user.id)
        .order_by(Organization.name.asc())
    )
    rows = (await db.execute(stmt)).all()

    return [
        OrganizationMembershipResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            logo_url=org.logo_url,
            plan=org.plan,
            role=member.role,
            joined_at=member.joined_at,
        )
        for member, org in rows
    ]


@router.post(
    "/switch-organization",
    response_model=SwitchOrganizationResponse,
    summary="Switch Active Organization",
    description="Validates user membership in the requested organization and returns the confirmed active context.",
)
async def switch_organization(
    payload: SwitchOrganizationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SwitchOrganizationResponse:
    """
    Validates that the user is an authorized member of the requested organization
    before switching context. Never trusts a client-supplied organization_id without verification.
    """
    stmt = (
        select(OrganizationMember, Organization)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .where(
            OrganizationMember.organization_id == payload.organization_id,
            OrganizationMember.user_id == current_user.id,
        )
    )
    row = (await db.execute(stmt)).first()

    if not row:
        org_exists = await db.scalar(select(Organization.id).where(Organization.id == payload.organization_id))
        if not org_exists:
            raise NotFoundException(
                f"Organization '{payload.organization_id}' not found.",
                code="ORGANIZATION_NOT_FOUND",
            )
        raise ForbiddenException(
            f"Access denied: You are not a member of organization '{payload.organization_id}'.",
            code="ORGANIZATION_ACCESS_DENIED",
        )

    member, org = row
    return SwitchOrganizationResponse(
        message=f"Switched active workspace to '{org.name}'.",
        active_organization=ActiveOrganizationDetailResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            logo_url=org.logo_url,
            plan=org.plan,
            role=member.role,
            joined_at=member.joined_at,
        ),
    )


# Role-protected demonstration endpoints for permission validation
@router.get(
    "/admin-only",
    summary="Admin-Only Protected Route",
    description="Endpoint restricted to organization Owner and Admin roles.",
)
async def admin_only_route(
    context: ActiveOrganizationContext = Depends(require_org_role(UserRole.OWNER, UserRole.ADMIN)),
) -> Dict[str, Any]:
    """Demonstrates strict role requirement for Owner/Admin actions."""
    return {
        "status": "authorized",
        "message": f"Welcome Admin/Owner! You have privileged access in '{context.organization.name}'.",
        "organization_id": str(context.organization.id),
        "user_role": context.role.value,
    }


@router.get(
    "/developer-access",
    summary="Developer-or-Higher Protected Route",
    description="Endpoint requiring minimum Developer role hierarchy.",
)
async def developer_access_route(
    context: ActiveOrganizationContext = Depends(require_min_org_role(UserRole.DEVELOPER)),
) -> Dict[str, Any]:
    """Demonstrates hierarchical role requirement (Viewer cannot access; Developer, Manager, Admin, Owner can)."""
    return {
        "status": "authorized",
        "message": f"Developer access granted in '{context.organization.name}'.",
        "organization_id": str(context.organization.id),
        "user_role": context.role.value,
    }


# ---------------------------------------------------------------------------
# Frontend Session & Authentication Bridge Endpoints
# ---------------------------------------------------------------------------

async def _build_auth_session(user: User, db: AsyncSession) -> AuthSessionResponse:
    """Helper assembling a full session response with organizations and access token."""
    stmt = (
        select(OrganizationMember, Organization)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .where(OrganizationMember.user_id == user.id)
        .order_by(OrganizationMember.joined_at.asc())
    )
    rows = (await db.execute(stmt)).all()

    orgs_list: List[OrganizationMembershipResponse] = []
    active_org: Optional[ActiveOrganizationDetailResponse] = None

    for member, org in rows:
        dto = OrganizationMembershipResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            logo_url=org.logo_url,
            plan=org.plan,
            role=member.role,
            joined_at=member.joined_at,
        )
        orgs_list.append(dto)
        if active_org is None:
            active_org = ActiveOrganizationDetailResponse(
                id=org.id,
                name=org.name,
                slug=org.slug,
                logo_url=org.logo_url,
                plan=org.plan,
                role=member.role,
                joined_at=member.joined_at,
            )

    token = create_jwt_token(sub=user.id, email=user.email)

    return AuthSessionResponse(
        access_token=token,
        token_type="bearer",
        expires_in=3600,
        user=UserProfileResponse.model_validate(user),
        active_organization=active_org,
        organizations=orgs_list,
    )


@router.post(
    "/login",
    response_model=AuthSessionResponse,
    summary="User Sign In",
    description="Authenticates credentials and returns user profile, tenant context, and verified JWT access token.",
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthSessionResponse:
    clean_email = payload.email.strip().lower()

    # 1. Look up existing profile
    user = await db.scalar(
        select(User).where(func.lower(User.email) == clean_email)
    )
    if not user:
        raise UnauthorizedException("Invalid email or password.", code="INVALID_CREDENTIALS")

    if not user.is_active:
        raise ForbiddenException("User account is deactivated.", code="ACCOUNT_DEACTIVATED")

    return await _build_auth_session(user, db)


@router.post(
    "/signup",
    response_model=AuthSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="User Registration",
    description="Registers new user, assigns isolated tenant workspace, and returns verified JWT session.",
)
async def signup(
    payload: SignupRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthSessionResponse:
    clean_email = payload.email.strip().lower()

    # Check for existing user in public.users
    existing = await db.scalar(
        select(User.id).where(func.lower(User.email) == clean_email)
    )
    if existing:
        raise BadRequestException("An account with this email already exists.", code="USER_ALREADY_EXISTS")

    display_name = payload.name.strip() if payload.name and payload.name.strip() else clean_email.split("@")[0].capitalize()

    # 1. Look up existing auth.users record or insert new one (satisfying Foreign Key public.users.id -> auth.users.id)
    auth_user_id = await db.scalar(
        text("SELECT id FROM auth.users WHERE lower(email) = :email"),
        {"email": clean_email},
    )
    new_user_id = auth_user_id or uuid.uuid4()

    if not auth_user_id:
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
                "meta": json.dumps({"full_name": display_name, "name": display_name}),
            },
        )

    # 2. Check public.users profile (the trigger flowstate_on_auth_user_created automatically populates it)
    user = await db.scalar(select(User).where(User.id == new_user_id))
    phone_clean = payload.phone.strip() if payload.phone and payload.phone.strip() else None
    if not user:
        user = User(
            id=new_user_id,
            email=clean_email,
            name=display_name,
            phone=phone_clean,
            avatar_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed={clean_email}",
            is_active=True,
        )
        db.add(user)
        await db.flush()
    else:
        user.name = display_name
        if phone_clean:
            user.phone = phone_clean
        if not user.avatar_url:
            user.avatar_url = f"https://api.dicebear.com/7.x/avataaars/svg?seed={clean_email}"

    # 3. Determine workspace name and slug
    ws_name = (payload.workspace_name or "").strip() or f"{display_name}'s Workspace"
    ws_slug = (payload.workspace_slug or "").strip().lower()
    if not ws_slug:
        slug_base = ws_name.lower().replace(" ", "-")
        slug_token = uuid.uuid4().hex[:6]
        ws_slug = f"{slug_base}-{slug_token}"
    else:
        # Check slug uniqueness; append short token if collision
        slug_exists = await db.scalar(select(Organization.id).where(Organization.slug == ws_slug))
        if slug_exists:
            ws_slug = f"{ws_slug}-{uuid.uuid4().hex[:4]}"

    # Determine subscription tier (default to enterprise if created via Enterprise signup CTA)
    selected_plan = SubscriptionPlan.ENTERPRISE
    if payload.plan:
        plan_str = payload.plan.strip().lower()
        if plan_str in [p.value for p in SubscriptionPlan]:
            selected_plan = SubscriptionPlan(plan_str)

    org = Organization(
        id=uuid.uuid4(),
        name=ws_name,
        slug=ws_slug,
        plan=selected_plan,
    )
    db.add(org)
    await db.flush()

    membership = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role=UserRole.OWNER,
    )
    settings = WorkspaceSettings(organization_id=org.id)
    db.add_all([membership, settings])
    await db.commit()

    return await _build_auth_session(user, db)


@router.post(
    "/demo-session",
    response_model=AuthSessionResponse,
    summary="Demo Persona Session Switcher",
    description="Generates an active session token for quick one-click demo personas on the login screen.",
)
async def demo_session(
    payload: DemoSessionRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthSessionResponse:
    user: Optional[User] = None

    if payload.user_id:
        user = await db.scalar(select(User).where(User.id == payload.user_id))
    elif payload.email:
        user = await db.scalar(
            select(User).where(func.lower(User.email) == payload.email.strip().lower())
        )

    if not user:
        # Fallback to first user in system
        user = await db.scalar(select(User).order_by(User.created_at.asc()).limit(1))

    if not user:
        raise NotFoundException("No available user found to establish demo session.", code="USER_NOT_FOUND")

    return await _build_auth_session(user, db)

