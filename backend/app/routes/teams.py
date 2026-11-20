import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.dependencies.auth import (
    ActiveOrganizationContext,
    get_active_organization,
    require_min_org_role,
)
from app.dependencies.database import get_db
from app.models.enums import UserRole
from app.models.organization import OrganizationMember
from app.models.team import Team, TeamMember
from app.models.user import User
from app.schemas.auth import UserProfileResponse
from app.schemas.team import (
    AddTeamMemberRequest,
    TeamCreateRequest,
    TeamMemberResponse,
    TeamResponse,
    TeamUpdateRequest,
)
from app.services.activity import record_activity

logger = logging.getLogger("flowstate.routes.teams")

router = APIRouter(tags=["Teams"])


async def get_team_in_org(
    team_id: uuid.UUID,
    org_id: uuid.UUID,
    db: AsyncSession,
) -> Team:
    """Helper verifying that a team exists within the specified tenant organization."""
    stmt = (
        select(Team)
        .options(selectinload(Team.lead))
        .where(Team.id == team_id, Team.organization_id == org_id)
    )
    team = (await db.execute(stmt)).scalar_one_or_none()
    if not team:
        raise NotFoundException(
            f"Team '{team_id}' not found in organization '{org_id}'.",
            code="TEAM_NOT_FOUND",
        )
    return team


def can_manage_team(ctx: ActiveOrganizationContext, team: Team) -> bool:
    """Checks if caller is Owner, Admin, Manager, or the assigned Team Lead."""
    if ctx.has_min_role(UserRole.MANAGER):
        return True
    return team.lead_id is not None and team.lead_id == ctx.user_id


# ---------------------------------------------------------------------------
# 1. Team CRUD Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/organizations/{organization_id}/teams",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Team (Org Path)",
)
@router.post(
    "/teams",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Team",
    description="Creates a new functional team within the active organization. Requires MANAGER, ADMIN, or OWNER role.",
)
async def create_team(
    payload: TeamCreateRequest,
    ctx: ActiveOrganizationContext = Depends(require_min_org_role(UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
) -> TeamResponse:
    org_id = ctx.organization_id

    # 1. Check for team name collision within the same organization
    existing = await db.scalar(
        select(Team.id).where(
            Team.organization_id == org_id,
            func.lower(Team.name) == payload.name.strip().lower(),
        )
    )
    if existing:
        raise BadRequestException(
            f"A team named '{payload.name.strip()}' already exists in this organization.",
            code="TEAM_NAME_COLLISION",
        )

    # 2. If lead_id provided, verify that the user is an enrolled organization member
    lead_user: Optional[User] = None
    if payload.lead_id:
        lead_membership = await db.scalar(
            select(OrganizationMember.id).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == payload.lead_id,
            )
        )
        if not lead_membership:
            raise BadRequestException(
                f"User '{payload.lead_id}' cannot be designated team lead because they are not a member of this organization.",
                code="INVALID_TEAM_LEAD",
            )
        lead_user = await db.scalar(select(User).where(User.id == payload.lead_id))

    # 3. Create Team entity
    team = Team(
        organization_id=org_id,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        lead_id=payload.lead_id,
    )
    db.add(team)
    await db.flush()

    # 4. Enroll initial members
    initial_member_ids = set(payload.member_ids or [])
    if payload.lead_id:
        initial_member_ids.add(payload.lead_id)

    members_to_create = []
    for uid in initial_member_ids:
        # Verify each user is an organization member
        is_org_member = await db.scalar(
            select(OrganizationMember.id).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == uid,
            )
        )
        if is_org_member:
            members_to_create.append(TeamMember(team_id=team.id, user_id=uid))

    if members_to_create:
        db.add_all(members_to_create)

    await db.commit()
    await db.refresh(team)

    return TeamResponse(
        id=team.id,
        organization_id=team.organization_id,
        name=team.name,
        description=team.description,
        lead_id=team.lead_id,
        lead=UserProfileResponse.model_validate(lead_user) if lead_user else None,
        members_count=len(members_to_create),
        created_at=team.created_at,
        updated_at=team.updated_at,
    )


@router.get(
    "/organizations/{organization_id}/teams",
    response_model=List[TeamResponse],
    summary="List Teams (Org Path)",
)
@router.get(
    "/teams",
    response_model=List[TeamResponse],
    summary="List Teams",
    description="Lists all functional teams in the active organization. Requires organization membership.",
)
async def list_teams(
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> List[TeamResponse]:
    org_id = ctx.organization_id

    stmt = (
        select(Team)
        .options(selectinload(Team.lead))
        .where(Team.organization_id == org_id)
        .order_by(Team.name.asc())
    )
    teams = (await db.execute(stmt)).scalars().all()

    results: List[TeamResponse] = []
    for t in teams:
        count = await db.scalar(
            select(func.count(TeamMember.user_id)).where(TeamMember.team_id == t.id)
        ) or 0
        results.append(
            TeamResponse(
                id=t.id,
                organization_id=t.organization_id,
                name=t.name,
                description=t.description,
                lead_id=t.lead_id,
                lead=UserProfileResponse.model_validate(t.lead) if t.lead else None,
                members_count=count,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
        )
    return results


@router.get(
    "/organizations/{organization_id}/teams/{team_id}",
    response_model=TeamResponse,
    summary="Get Team Details (Org Path)",
)
@router.get(
    "/teams/{team_id}",
    response_model=TeamResponse,
    summary="Get Team Details",
    description="Retrieves comprehensive team details and member list.",
)
async def get_team(
    team_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> TeamResponse:
    team = await get_team_in_org(team_id, ctx.organization_id, db)

    members_stmt = (
        select(TeamMember)
        .options(selectinload(TeamMember.user))
        .where(TeamMember.team_id == team.id)
        .order_by(TeamMember.joined_at.asc())
    )
    members = (await db.execute(members_stmt)).scalars().all()

    member_responses = [
        TeamMemberResponse(
            team_id=m.team_id,
            user_id=m.user_id,
            joined_at=m.joined_at,
            user=UserProfileResponse.model_validate(m.user) if m.user else None,
        )
        for m in members
    ]

    return TeamResponse(
        id=team.id,
        organization_id=team.organization_id,
        name=team.name,
        description=team.description,
        lead_id=team.lead_id,
        lead=UserProfileResponse.model_validate(team.lead) if team.lead else None,
        members_count=len(members),
        members=member_responses,
        created_at=team.created_at,
        updated_at=team.updated_at,
    )


@router.patch(
    "/organizations/{organization_id}/teams/{team_id}",
    response_model=TeamResponse,
    summary="Update Team (Org Path)",
)
@router.patch(
    "/teams/{team_id}",
    response_model=TeamResponse,
    summary="Update Team",
    description="Modifies team name, description, or lead. Requires MANAGER, ADMIN, OWNER, or Team Lead.",
)
async def update_team(
    team_id: uuid.UUID,
    payload: TeamUpdateRequest,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> TeamResponse:
    team = await get_team_in_org(team_id, ctx.organization_id, db)

    # Authorization guard: must be Manager+, or current Team Lead
    if not can_manage_team(ctx, team):
        raise ForbiddenException(
            "Access denied: Modifying team details requires Manager, Admin, Owner, or Team Lead status.",
            code="INSUFFICIENT_ROLE_PERMISSIONS",
        )

    # Name uniqueness check if changed
    if payload.name is not None:
        clean_name = payload.name.strip()
        if clean_name.lower() != team.name.lower():
            existing = await db.scalar(
                select(Team.id).where(
                    Team.organization_id == ctx.organization_id,
                    func.lower(Team.name) == clean_name.lower(),
                    Team.id != team.id,
                )
            )
            if existing:
                raise BadRequestException(f"Team name '{clean_name}' is already taken.", code="TEAM_NAME_COLLISION")
            team.name = clean_name

    if payload.description is not None:
        team.description = payload.description.strip() if payload.description.strip() else None

    # Lead change check
    lead_user = team.lead
    if payload.lead_id is not None:
        if payload.lead_id != team.lead_id:
            lead_membership = await db.scalar(
                select(OrganizationMember.id).where(
                    OrganizationMember.organization_id == ctx.organization_id,
                    OrganizationMember.user_id == payload.lead_id,
                )
            )
            if not lead_membership:
                raise BadRequestException(
                    f"User '{payload.lead_id}' cannot be designated team lead because they are not an organization member.",
                    code="INVALID_TEAM_LEAD",
                )
            team.lead_id = payload.lead_id
            lead_user = await db.scalar(select(User).where(User.id == payload.lead_id))

            # Automatically ensure new lead is enrolled in team members
            is_mem = await db.scalar(
                select(TeamMember.user_id).where(TeamMember.team_id == team.id, TeamMember.user_id == payload.lead_id)
            )
            if not is_mem:
                db.add(TeamMember(team_id=team.id, user_id=payload.lead_id))

    await db.commit()
    await db.refresh(team)

    count = await db.scalar(
        select(func.count(TeamMember.user_id)).where(TeamMember.team_id == team.id)
    ) or 0

    return TeamResponse(
        id=team.id,
        organization_id=team.organization_id,
        name=team.name,
        description=team.description,
        lead_id=team.lead_id,
        lead=UserProfileResponse.model_validate(lead_user) if lead_user else None,
        members_count=count,
        created_at=team.created_at,
        updated_at=team.updated_at,
    )


@router.delete(
    "/organizations/{organization_id}/teams/{team_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Team (Org Path)",
)
@router.delete(
    "/teams/{team_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Team",
    description="Deletes a functional team. Requires OWNER or ADMIN role.",
)
async def delete_team(
    team_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(require_min_org_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    team = await get_team_in_org(team_id, ctx.organization_id, db)

    team_name = team.name
    await db.delete(team)
    await db.commit()

    return {
        "status": "success",
        "message": f"Team '{team_name}' was successfully deleted.",
        "team_id": str(team_id),
    }


# ---------------------------------------------------------------------------
# 2. Team Member Management
# ---------------------------------------------------------------------------

@router.get(
    "/organizations/{organization_id}/teams/{team_id}/members",
    response_model=List[TeamMemberResponse],
    summary="List Team Members (Org Path)",
)
@router.get(
    "/teams/{team_id}/members",
    response_model=List[TeamMemberResponse],
    summary="List Team Members",
    description="Lists all users enrolled in this team.",
)
async def list_team_members(
    team_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> List[TeamMemberResponse]:
    await get_team_in_org(team_id, ctx.organization_id, db)

    stmt = (
        select(TeamMember)
        .options(selectinload(TeamMember.user))
        .where(TeamMember.team_id == team_id)
        .order_by(TeamMember.joined_at.asc())
    )
    members = (await db.execute(stmt)).scalars().all()

    return [
        TeamMemberResponse(
            team_id=m.team_id,
            user_id=m.user_id,
            joined_at=m.joined_at,
            user=UserProfileResponse.model_validate(m.user) if m.user else None,
        )
        for m in members
    ]


@router.post(
    "/organizations/{organization_id}/teams/{team_id}/members",
    response_model=TeamMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Team Member (Org Path)",
)
@router.post(
    "/teams/{team_id}/members",
    response_model=TeamMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Team Member",
    description="Enrolls an organization user into the team. Requires MANAGER, ADMIN, OWNER, or Team Lead.",
)
async def add_team_member(
    team_id: uuid.UUID,
    payload: AddTeamMemberRequest,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> TeamMemberResponse:
    team = await get_team_in_org(team_id, ctx.organization_id, db)

    # 1. Permission check
    if not can_manage_team(ctx, team):
        raise ForbiddenException(
            "Access denied: Adding members requires Manager, Admin, Owner, or Team Lead status.",
            code="INSUFFICIENT_ROLE_PERMISSIONS",
        )

    # 2. Locate target user
    target_user: Optional[User] = None
    if payload.user_id:
        target_user = await db.scalar(select(User).where(User.id == payload.user_id))
    elif payload.email and payload.email.strip():
        target_user = await db.scalar(select(User).where(func.lower(User.email) == payload.email.strip().lower()))
    else:
        raise BadRequestException("Either 'user_id' or 'email' must be provided.", code="MISSING_TARGET_USER")

    if not target_user:
        raise NotFoundException("User not found.", code="USER_NOT_FOUND")

    # 3. Verify user belongs to the tenant organization
    is_org_member = await db.scalar(
        select(OrganizationMember.id).where(
            OrganizationMember.organization_id == ctx.organization_id,
            OrganizationMember.user_id == target_user.id,
        )
    )
    if not is_org_member:
        raise BadRequestException(
            f"User '{target_user.email}' is not a member of this organization. Enroll them in the organization first.",
            code="USER_NOT_ORGANIZATION_MEMBER",
        )

    # 4. Check for duplicate membership
    already_member = await db.scalar(
        select(TeamMember.user_id).where(TeamMember.team_id == team_id, TeamMember.user_id == target_user.id)
    )
    if already_member:
        raise BadRequestException("User is already a member of this team.", code="MEMBER_ALREADY_IN_TEAM")

    # 5. Insert TeamMember
    new_member = TeamMember(team_id=team.id, user_id=target_user.id)
    db.add(new_member)

    await record_activity(
        db=db,
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        action="team_membership_changed",
        target_type="team",
        target_id=team.id,
        target_title=team.name,
        details={"change": "member_added", "user_id": str(target_user.id), "email": target_user.email},
    )

    await db.commit()
    await db.refresh(new_member)

    return TeamMemberResponse(
        team_id=new_member.team_id,
        user_id=new_member.user_id,
        joined_at=new_member.joined_at,
        user=UserProfileResponse.model_validate(target_user),
    )


@router.delete(
    "/organizations/{organization_id}/teams/{team_id}/members/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove Team Member (Org Path)",
)
@router.delete(
    "/teams/{team_id}/members/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove Team Member",
    description="Removes a user from the team. Users can leave voluntarily; Managers/Admins/Owners/Team Leads can remove others.",
)
async def remove_team_member(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> dict:
    team = await get_team_in_org(team_id, ctx.organization_id, db)

    member_record = await db.scalar(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )
    if not member_record:
        raise NotFoundException(f"User '{user_id}' is not a member of this team.", code="TEAM_MEMBER_NOT_FOUND")

    # Permission check: Self-leave is allowed; otherwise requires can_manage_team
    if ctx.user_id != user_id and not can_manage_team(ctx, team):
        raise ForbiddenException(
            "Access denied: Removing other team members requires Manager, Admin, Owner, or Team Lead status.",
            code="INSUFFICIENT_ROLE_PERMISSIONS",
        )

    await db.delete(member_record)

    await record_activity(
        db=db,
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        action="team_membership_changed",
        target_type="team",
        target_id=team.id,
        target_title=team.name,
        details={"change": "member_removed", "user_id": str(user_id)},
    )

    await db.commit()

    return {
        "status": "success",
        "message": f"User '{user_id}' was removed from team '{team.name}'.",
        "team_id": str(team_id),
        "user_id": str(user_id),
    }
