import logging
import re
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
from app.models.enums import PriorityLevel, ProjectStatus, UserRole
from app.models.organization import OrganizationMember
from app.models.project import Project, ProjectMember
from app.models.team import Team
from app.models.user import User
from app.schemas.auth import UserProfileResponse
from app.schemas.project import (
    AddProjectMemberRequest,
    ProjectCreateRequest,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.services.activity import record_activity

logger = logging.getLogger("flowstate.routes.projects")

router = APIRouter(tags=["Projects"])


def derive_project_key(name: str) -> str:
    """Derives a concise uppercase alphanumeric prefix from project name."""
    cleaned = re.sub(r"[^A-Za-z0-9]", "", name).upper()
    if len(cleaned) >= 3:
        return cleaned[:4]
    return (cleaned + "PRJ")[:3]


async def get_project_in_org(
    project_id: uuid.UUID,
    org_id: uuid.UUID,
    db: AsyncSession,
) -> Project:
    """Helper verifying that a project exists within the specified tenant organization."""
    stmt = (
        select(Project)
        .options(selectinload(Project.manager), selectinload(Project.team))
        .where(Project.id == project_id, Project.organization_id == org_id)
    )
    project = (await db.execute(stmt)).scalar_one_or_none()
    if not project:
        raise NotFoundException(
            f"Project '{project_id}' not found in organization '{org_id}'.",
            code="PROJECT_NOT_FOUND",
        )
    return project


def can_manage_project(ctx: ActiveOrganizationContext, project: Project) -> bool:
    """Checks if caller is Owner, Admin, Manager, or the assigned Project Manager."""
    if ctx.has_min_role(UserRole.MANAGER):
        return True
    return project.manager_id is not None and project.manager_id == ctx.user_id


# ---------------------------------------------------------------------------
# 1. Project CRUD Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/organizations/{organization_id}/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Project (Org Path)",
)
@router.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Project",
    description="Creates a new project container. Requires MANAGER, ADMIN, or OWNER role.",
)
async def create_project(
    payload: ProjectCreateRequest,
    ctx: ActiveOrganizationContext = Depends(require_min_org_role(UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    org_id = ctx.organization_id

    # 1. Project Key resolution & validation
    if payload.key:
        target_key = payload.key.strip().upper()
        existing_key = await db.scalar(
            select(Project.id).where(
                Project.organization_id == org_id,
                Project.key == target_key,
            )
        )
        if existing_key:
            raise BadRequestException(
                f"Project key '{target_key}' is already in use in this organization.",
                code="PROJECT_KEY_COLLISION",
            )
    else:
        base_key = derive_project_key(payload.name)
        target_key = base_key
        counter = 1
        while await db.scalar(
            select(Project.id).where(Project.organization_id == org_id, Project.key == target_key)
        ):
            counter += 1
            target_key = f"{base_key[:3]}{counter}"

    # 2. Team reference validation
    if payload.team_id:
        valid_team = await db.scalar(
            select(Team.id).where(Team.id == payload.team_id, Team.organization_id == org_id)
        )
        if not valid_team:
            raise BadRequestException(
                f"Team '{payload.team_id}' does not exist in this organization.",
                code="INVALID_TEAM",
            )

    # 3. Manager reference validation
    manager_user: Optional[User] = None
    if payload.manager_id:
        is_org_member = await db.scalar(
            select(OrganizationMember.id).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == payload.manager_id,
            )
        )
        if not is_org_member:
            raise BadRequestException(
                f"User '{payload.manager_id}' cannot be designated manager because they are not an organization member.",
                code="INVALID_PROJECT_MANAGER",
            )
        manager_user = await db.scalar(select(User).where(User.id == payload.manager_id))

    # 4. Create Project entity
    new_project = Project(
        organization_id=org_id,
        team_id=payload.team_id,
        key=target_key,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        status=payload.status,
        priority=payload.priority,
        color=payload.color.strip(),
        start_date=payload.start_date,
        due_date=payload.due_date,
        manager_id=payload.manager_id,
        progress=0,
        budget=payload.budget,
        spent=0,
        last_task_number=100,
    )
    db.add(new_project)
    await db.flush()

    # 5. Enroll initial project members (include creator, manager, and any payload member_ids)
    initial_member_ids = set(payload.member_ids or [])
    if payload.manager_id:
        initial_member_ids.add(payload.manager_id)
    initial_member_ids.add(ctx.user_id)

    members_to_create = []
    for uid in initial_member_ids:
        is_mem = await db.scalar(
            select(OrganizationMember.id).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == uid,
            )
        )
        if is_mem:
            members_to_create.append(ProjectMember(project_id=new_project.id, user_id=uid))

    if members_to_create:
        db.add_all(members_to_create)

    await record_activity(
        db=db,
        organization_id=org_id,
        user_id=ctx.user_id,
        action="project_created",
        target_type="project",
        target_id=new_project.id,
        target_title=new_project.name,
        project_id=new_project.id,
        details={"key": new_project.key, "status": new_project.status.value},
    )

    await db.commit()
    await db.refresh(new_project)

    return ProjectResponse(
        id=new_project.id,
        organization_id=new_project.organization_id,
        team_id=new_project.team_id,
        key=new_project.key,
        name=new_project.name,
        description=new_project.description,
        status=new_project.status,
        priority=new_project.priority,
        color=new_project.color,
        start_date=new_project.start_date,
        due_date=new_project.due_date,
        manager_id=new_project.manager_id,
        manager=UserProfileResponse.model_validate(manager_user) if manager_user else None,
        progress=new_project.progress,
        budget=new_project.budget,
        spent=new_project.spent,
        last_task_number=new_project.last_task_number,
        members_count=len(members_to_create),
        created_at=new_project.created_at,
        updated_at=new_project.updated_at,
    )


@router.get(
    "/organizations/{organization_id}/projects",
    response_model=List[ProjectResponse],
    summary="List Projects (Org Path)",
)
@router.get(
    "/projects",
    response_model=List[ProjectResponse],
    summary="List Projects",
    description="Lists all projects in the active organization with optional team, status, and priority filters.",
)
async def list_projects(
    team_id: Optional[uuid.UUID] = Query(None, description="Filter by owning team"),
    project_status: Optional[ProjectStatus] = Query(None, alias="status", description="Filter by project status"),
    priority: Optional[PriorityLevel] = Query(None, description="Filter by priority level"),
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> List[ProjectResponse]:
    org_id = ctx.organization_id

    stmt = (
        select(Project)
        .options(selectinload(Project.manager))
        .where(Project.organization_id == org_id)
    )
    if team_id:
        stmt = stmt.where(Project.team_id == team_id)
    if project_status:
        stmt = stmt.where(Project.status == project_status)
    if priority:
        stmt = stmt.where(Project.priority == priority)

    stmt = stmt.order_by(Project.created_at.desc())
    projects = (await db.execute(stmt)).scalars().all()

    results: List[ProjectResponse] = []
    for p in projects:
        count = await db.scalar(
            select(func.count(ProjectMember.user_id)).where(ProjectMember.project_id == p.id)
        ) or 0
        results.append(
            ProjectResponse(
                id=p.id,
                organization_id=p.organization_id,
                team_id=p.team_id,
                key=p.key,
                name=p.name,
                description=p.description,
                status=p.status,
                priority=p.priority,
                color=p.color,
                start_date=p.start_date,
                due_date=p.due_date,
                manager_id=p.manager_id,
                manager=UserProfileResponse.model_validate(p.manager) if p.manager else None,
                progress=p.progress,
                budget=p.budget,
                spent=p.spent,
                last_task_number=p.last_task_number,
                members_count=count,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
        )
    return results


@router.get(
    "/organizations/{organization_id}/projects/{project_id}",
    response_model=ProjectResponse,
    summary="Get Project Details (Org Path)",
)
@router.get(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    summary="Get Project Details",
    description="Retrieves comprehensive project container details and members.",
)
async def get_project(
    project_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    project = await get_project_in_org(project_id, ctx.organization_id, db)

    members_stmt = (
        select(ProjectMember)
        .options(selectinload(ProjectMember.user))
        .where(ProjectMember.project_id == project.id)
        .order_by(ProjectMember.joined_at.asc())
    )
    members = (await db.execute(members_stmt)).scalars().all()

    member_responses = [
        ProjectMemberResponse(
            project_id=m.project_id,
            user_id=m.user_id,
            joined_at=m.joined_at,
            user=UserProfileResponse.model_validate(m.user) if m.user else None,
        )
        for m in members
    ]

    return ProjectResponse(
        id=project.id,
        organization_id=project.organization_id,
        team_id=project.team_id,
        key=project.key,
        name=project.name,
        description=project.description,
        status=project.status,
        priority=project.priority,
        color=project.color,
        start_date=project.start_date,
        due_date=project.due_date,
        manager_id=project.manager_id,
        manager=UserProfileResponse.model_validate(project.manager) if project.manager else None,
        progress=project.progress,
        budget=project.budget,
        spent=project.spent,
        last_task_number=project.last_task_number,
        members_count=len(members),
        members=member_responses,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.patch(
    "/organizations/{organization_id}/projects/{project_id}",
    response_model=ProjectResponse,
    summary="Update Project (Org Path)",
)
@router.patch(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    summary="Update Project",
    description="Updates project metadata, status, progress, or team. Requires MANAGER, ADMIN, OWNER, or Project Manager.",
)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdateRequest,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    project = await get_project_in_org(project_id, ctx.organization_id, db)

    # Authorization guard: must be Manager+, or current Project Manager
    if not can_manage_project(ctx, project):
        raise ForbiddenException(
            "Access denied: Modifying project details requires Manager, Admin, Owner, or Project Manager status.",
            code="INSUFFICIENT_ROLE_PERMISSIONS",
        )

    # Key uniqueness check if changed
    if payload.key is not None:
        target_key = payload.key.strip().upper()
        if target_key != project.key:
            existing = await db.scalar(
                select(Project.id).where(
                    Project.organization_id == ctx.organization_id,
                    Project.key == target_key,
                    Project.id != project.id,
                )
            )
            if existing:
                raise BadRequestException(f"Project key '{target_key}' is already in use.", code="PROJECT_KEY_COLLISION")
            project.key = target_key

    # Team check if changed
    if payload.team_id is not None:
        valid_team = await db.scalar(
            select(Team.id).where(Team.id == payload.team_id, Team.organization_id == ctx.organization_id)
        )
        if not valid_team:
            raise BadRequestException("Target team does not exist in this organization.", code="INVALID_TEAM")
        project.team_id = payload.team_id

    # Manager check if changed
    manager_user = project.manager
    if payload.manager_id is not None:
        if payload.manager_id != project.manager_id:
            is_org_member = await db.scalar(
                select(OrganizationMember.id).where(
                    OrganizationMember.organization_id == ctx.organization_id,
                    OrganizationMember.user_id == payload.manager_id,
                )
            )
            if not is_org_member:
                raise BadRequestException("Designated manager must be an organization member.", code="INVALID_PROJECT_MANAGER")
            project.manager_id = payload.manager_id
            manager_user = await db.scalar(select(User).where(User.id == payload.manager_id))

            # Automatically ensure new manager is enrolled in project members
            is_mem = await db.scalar(
                select(ProjectMember.user_id).where(
                    ProjectMember.project_id == project.id,
                    ProjectMember.user_id == payload.manager_id,
                )
            )
            if not is_mem:
                db.add(ProjectMember(project_id=project.id, user_id=payload.manager_id))

    if payload.name is not None:
        project.name = payload.name.strip()
    if payload.description is not None:
        project.description = payload.description.strip() if payload.description.strip() else None
    if payload.status is not None:
        project.status = payload.status
    if payload.priority is not None:
        project.priority = payload.priority
    if payload.color is not None:
        project.color = payload.color.strip()
    if payload.start_date is not None:
        project.start_date = payload.start_date
    if payload.due_date is not None:
        project.due_date = payload.due_date
    if payload.progress is not None:
        project.progress = payload.progress
    if payload.budget is not None:
        project.budget = payload.budget
    if payload.spent is not None:
        project.spent = payload.spent

    await record_activity(
        db=db,
        organization_id=project.organization_id,
        user_id=ctx.user_id,
        action="project_updated",
        target_type="project",
        target_id=project.id,
        target_title=project.name,
        project_id=project.id,
        details={"status": project.status.value, "progress": project.progress},
    )

    await db.commit()
    await db.refresh(project)

    count = await db.scalar(
        select(func.count(ProjectMember.user_id)).where(ProjectMember.project_id == project.id)
    ) or 0

    return ProjectResponse(
        id=project.id,
        organization_id=project.organization_id,
        team_id=project.team_id,
        key=project.key,
        name=project.name,
        description=project.description,
        status=project.status,
        priority=project.priority,
        color=project.color,
        start_date=project.start_date,
        due_date=project.due_date,
        manager_id=project.manager_id,
        manager=UserProfileResponse.model_validate(manager_user) if manager_user else None,
        progress=project.progress,
        budget=project.budget,
        spent=project.spent,
        last_task_number=project.last_task_number,
        members_count=count,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.delete(
    "/organizations/{organization_id}/projects/{project_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Project (Org Path)",
)
@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Project",
    description="Deletes a project container. Requires OWNER or ADMIN role.",
)
async def delete_project(
    project_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(require_min_org_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    project = await get_project_in_org(project_id, ctx.organization_id, db)

    project_name = project.name
    await db.delete(project)
    await db.commit()

    return {
        "status": "success",
        "message": f"Project '{project_name}' was successfully deleted.",
        "project_id": str(project_id),
    }


# ---------------------------------------------------------------------------
# 2. Project Member Management
# ---------------------------------------------------------------------------

@router.get(
    "/organizations/{organization_id}/projects/{project_id}/members",
    response_model=List[ProjectMemberResponse],
    summary="List Project Members (Org Path)",
)
@router.get(
    "/projects/{project_id}/members",
    response_model=List[ProjectMemberResponse],
    summary="List Project Members",
    description="Lists all users assigned to this project.",
)
async def list_project_members(
    project_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> List[ProjectMemberResponse]:
    await get_project_in_org(project_id, ctx.organization_id, db)

    stmt = (
        select(ProjectMember)
        .options(selectinload(ProjectMember.user))
        .where(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.joined_at.asc())
    )
    members = (await db.execute(stmt)).scalars().all()

    return [
        ProjectMemberResponse(
            project_id=m.project_id,
            user_id=m.user_id,
            joined_at=m.joined_at,
            user=UserProfileResponse.model_validate(m.user) if m.user else None,
        )
        for m in members
    ]


@router.post(
    "/organizations/{organization_id}/projects/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Project Member (Org Path)",
)
@router.post(
    "/projects/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Project Member",
    description="Assigns an organization user to the project. Requires MANAGER, ADMIN, OWNER, or Project Manager.",
)
async def add_project_member(
    project_id: uuid.UUID,
    payload: AddProjectMemberRequest,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> ProjectMemberResponse:
    project = await get_project_in_org(project_id, ctx.organization_id, db)

    if not can_manage_project(ctx, project):
        raise ForbiddenException(
            "Access denied: Assigning project members requires Manager, Admin, Owner, or Project Manager status.",
            code="INSUFFICIENT_ROLE_PERMISSIONS",
        )

    target_user: Optional[User] = None
    if payload.user_id:
        target_user = await db.scalar(select(User).where(User.id == payload.user_id))
    elif payload.email and payload.email.strip():
        target_user = await db.scalar(select(User).where(func.lower(User.email) == payload.email.strip().lower()))
    else:
        raise BadRequestException("Either 'user_id' or 'email' must be provided.", code="MISSING_TARGET_USER")

    if not target_user:
        raise NotFoundException("User not found.", code="USER_NOT_FOUND")

    is_org_member = await db.scalar(
        select(OrganizationMember.id).where(
            OrganizationMember.organization_id == ctx.organization_id,
            OrganizationMember.user_id == target_user.id,
        )
    )
    if not is_org_member:
        raise BadRequestException(
            f"User '{target_user.email}' is not an organization member. Enroll them in the organization first.",
            code="USER_NOT_ORGANIZATION_MEMBER",
        )

    already_assigned = await db.scalar(
        select(ProjectMember.user_id).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == target_user.id,
        )
    )
    if already_assigned:
        raise BadRequestException("User is already assigned to this project.", code="MEMBER_ALREADY_IN_PROJECT")

    new_member = ProjectMember(project_id=project.id, user_id=target_user.id)
    db.add(new_member)
    await db.commit()
    await db.refresh(new_member)

    return ProjectMemberResponse(
        project_id=new_member.project_id,
        user_id=new_member.user_id,
        joined_at=new_member.joined_at,
        user=UserProfileResponse.model_validate(target_user),
    )


@router.delete(
    "/organizations/{organization_id}/projects/{project_id}/members/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove Project Member (Org Path)",
)
@router.delete(
    "/projects/{project_id}/members/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove Project Member",
    description="Removes an assigned user from the project. Users can leave voluntarily; Managers/Admins/Owners/Project Managers can remove others.",
)
async def remove_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> dict:
    project = await get_project_in_org(project_id, ctx.organization_id, db)

    member_record = await db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    if not member_record:
        raise NotFoundException(f"User '{user_id}' is not assigned to this project.", code="PROJECT_MEMBER_NOT_FOUND")

    if ctx.user_id != user_id and not can_manage_project(ctx, project):
        raise ForbiddenException(
            "Access denied: Removing other project members requires Manager, Admin, Owner, or Project Manager status.",
            code="INSUFFICIENT_ROLE_PERMISSIONS",
        )

    await db.delete(member_record)
    await db.commit()

    return {
        "status": "success",
        "message": f"User '{user_id}' was removed from project '{project.name}'.",
        "project_id": str(project_id),
        "user_id": str(user_id),
    }
