import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException
from app.dependencies.auth import (
    ActiveOrganizationContext,
    get_active_organization,
)
from app.dependencies.database import get_db
from app.models.collaboration import Activity
from app.models.enums import PriorityLevel, ProjectStatus, TaskStatus
from app.models.organization import OrganizationMember
from app.models.project import Project
from app.models.task import Task
from app.models.team import Team, TeamMember
from app.models.user import User
from app.schemas.collaboration import ActivityListResponse, ActivityResponse
from app.schemas.dashboard import (
    DashboardOverviewResponse,
    MemberWorkloadStatItem,
    ProjectAnalyticsResponse,
    ProjectStatItem,
    ProjectStatsResponse,
    TaskStatsResponse,
    TeamAnalyticsResponse,
    TeamStatsResponse,
)

logger = logging.getLogger("flowstate.routes.dashboard")

router = APIRouter(tags=["Workspace Dashboard & Analytics"])


# ---------------------------------------------------------------------------
# 1. Dashboard Overview
# ---------------------------------------------------------------------------

@router.get(
    "/dashboard/overview",
    response_model=DashboardOverviewResponse,
    summary="Get Workspace Overview KPIs",
    description="Calculates top-level workspace KPI metrics entirely via SQL aggregation.",
)
async def get_dashboard_overview(
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> DashboardOverviewResponse:
    org_id = ctx.organization_id
    today = date.today()
    upcoming_limit = today + timedelta(days=7)

    # 1. Project stats aggregation
    proj_stmt = select(
        func.count(Project.id).label("total"),
        func.count(case((Project.status != ProjectStatus.COMPLETED, Project.id))).label("active"),
        func.count(case((Project.status == ProjectStatus.COMPLETED, Project.id))).label("completed"),
    ).where(Project.organization_id == org_id)
    proj_res = (await db.execute(proj_stmt)).one()

    # 2. Task stats aggregation
    task_stmt = select(
        func.count(Task.id).label("total"),
        func.count(case((Task.status == TaskStatus.DONE, Task.id))).label("completed"),
        func.count(case((Task.status == TaskStatus.IN_PROGRESS, Task.id))).label("in_progress"),
        func.count(
            case(((Task.status != TaskStatus.DONE) & (Task.due_date < today), Task.id))
        ).label("overdue"),
        func.count(
            case(
                (
                    (Task.status != TaskStatus.DONE)
                    & (Task.due_date >= today)
                    & (Task.due_date <= upcoming_limit),
                    Task.id,
                )
            )
        ).label("upcoming"),
    ).where(Task.organization_id == org_id)
    task_res = (await db.execute(task_stmt)).one()

    # 3. Organization Members count
    member_count_stmt = select(func.count(OrganizationMember.id)).where(
        OrganizationMember.organization_id == org_id
    )
    total_members = (await db.execute(member_count_stmt)).scalar() or 0

    # 4. Caller's Personal Tasks KPI Summary
    my_tasks_stmt = select(
        func.count(Task.id).label("total"),
        func.count(case((Task.status == TaskStatus.DONE, Task.id))).label("completed"),
        func.count(case((Task.status == TaskStatus.IN_PROGRESS, Task.id))).label("in_progress"),
        func.count(
            case(((Task.status != TaskStatus.DONE) & (Task.due_date < today), Task.id))
        ).label("overdue"),
    ).where(Task.organization_id == org_id, Task.assignee_id == ctx.user_id)
    my_tasks_res = (await db.execute(my_tasks_stmt)).one()

    return DashboardOverviewResponse(
        total_projects=proj_res.total or 0,
        active_projects=proj_res.active or 0,
        completed_projects=proj_res.completed or 0,
        total_tasks=task_res.total or 0,
        completed_tasks=task_res.completed or 0,
        in_progress_tasks=task_res.in_progress or 0,
        overdue_tasks=task_res.overdue or 0,
        upcoming_deadlines=task_res.upcoming or 0,
        total_team_members=total_members,
        my_tasks_summary={
            "total": my_tasks_res.total or 0,
            "completed": my_tasks_res.completed or 0,
            "in_progress": my_tasks_res.in_progress or 0,
            "overdue": my_tasks_res.overdue or 0,
        },
    )


# ---------------------------------------------------------------------------
# 2. Task Statistics
# ---------------------------------------------------------------------------

@router.get(
    "/dashboard/task-stats",
    response_model=TaskStatsResponse,
    summary="Get Workspace Task Statistics",
    description="Returns workspace-level task distributions across status, priority, and logged hours.",
)
async def get_dashboard_task_stats(
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> TaskStatsResponse:
    org_id = ctx.organization_id
    today = date.today()

    # Core task counters
    core_stmt = select(
        func.count(Task.id).label("total"),
        func.count(case((Task.status == TaskStatus.DONE, Task.id))).label("completed"),
        func.count(case((Task.status == TaskStatus.IN_PROGRESS, Task.id))).label("in_progress"),
        func.count(
            case(((Task.status != TaskStatus.DONE) & (Task.due_date < today), Task.id))
        ).label("overdue"),
        func.coalesce(func.sum(Task.estimated_hours), 0).label("est_hours"),
        func.coalesce(func.sum(Task.actual_hours), 0).label("act_hours"),
    ).where(Task.organization_id == org_id)
    core = (await db.execute(core_stmt)).one()

    total_tasks = core.total or 0
    completed_tasks = core.completed or 0
    completion_rate = round((completed_tasks / total_tasks * 100), 2) if total_tasks > 0 else 0.0

    # Group by Status
    status_stmt = (
        select(Task.status, func.count(Task.id))
        .where(Task.organization_id == org_id)
        .group_by(Task.status)
    )
    status_rows = (await db.execute(status_stmt)).all()
    tasks_by_status = {s.value: 0 for s in TaskStatus}
    for st, count in status_rows:
        tasks_by_status[st.value] = count

    # Group by Priority
    priority_stmt = (
        select(Task.priority, func.count(Task.id))
        .where(Task.organization_id == org_id)
        .group_by(Task.priority)
    )
    priority_rows = (await db.execute(priority_stmt)).all()
    tasks_by_priority = {p.value: 0 for p in PriorityLevel}
    for pr, count in priority_rows:
        tasks_by_priority[pr.value] = count

    return TaskStatsResponse(
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        in_progress_tasks=core.in_progress or 0,
        overdue_tasks=core.overdue or 0,
        completion_rate=completion_rate,
        tasks_by_status=tasks_by_status,
        tasks_by_priority=tasks_by_priority,
        total_estimated_hours=float(core.est_hours or 0.0),
        total_actual_hours=float(core.act_hours or 0.0),
    )


# ---------------------------------------------------------------------------
# 3. Project Statistics
# ---------------------------------------------------------------------------

@router.get(
    "/dashboard/project-stats",
    response_model=ProjectStatsResponse,
    summary="Get Workspace Project Statistics",
    description="Aggregates progress, budgets, and task health for all projects in the workspace.",
)
async def get_dashboard_project_stats(
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> ProjectStatsResponse:
    org_id = ctx.organization_id
    today = date.today()

    # Query projects with left-joined task counts
    stmt = (
        select(
            Project,
            func.count(Task.id).label("total_tasks"),
            func.count(case((Task.status == TaskStatus.DONE, Task.id))).label("completed_tasks"),
            func.count(
                case(((Task.status != TaskStatus.DONE) & (Task.due_date < today), Task.id))
            ).label("overdue_tasks"),
        )
        .outerjoin(Task, Task.project_id == Project.id)
        .where(Project.organization_id == org_id)
        .group_by(Project.id)
        .order_by(Project.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()

    project_items: List[ProjectStatItem] = []
    for proj, total_t, comp_t, overdue_t in rows:
        total_tasks = total_t or 0
        completed_tasks = comp_t or 0
        calculated_progress = (
            int(round((completed_tasks / total_tasks * 100)))
            if total_tasks > 0
            else proj.progress
        )
        is_overdue = bool(proj.due_date and proj.due_date < today and proj.status != ProjectStatus.COMPLETED)

        project_items.append(
            ProjectStatItem(
                id=proj.id,
                key=proj.key,
                name=proj.name,
                status=proj.status,
                priority=proj.priority,
                color=proj.color,
                progress=proj.progress,
                calculated_progress=calculated_progress,
                total_tasks=total_tasks,
                completed_tasks=completed_tasks,
                overdue_tasks=overdue_t or 0,
                start_date=proj.start_date,
                due_date=proj.due_date,
                is_overdue=is_overdue,
                spent=proj.spent,
                budget=proj.budget,
            )
        )

    return ProjectStatsResponse(
        total_projects=len(project_items),
        projects=project_items,
    )


# ---------------------------------------------------------------------------
# 4. Team Workload Statistics
# ---------------------------------------------------------------------------

@router.get(
    "/dashboard/team-stats",
    response_model=TeamStatsResponse,
    summary="Get Workspace Team Workload Statistics",
    description="Returns workload distribution and output efficiency per member across the organization.",
)
async def get_dashboard_team_stats(
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> TeamStatsResponse:
    org_id = ctx.organization_id
    today = date.today()

    # Total active tasks in workspace (for workload share percentage)
    active_tasks_stmt = select(func.count(Task.id)).where(
        Task.organization_id == org_id,
        Task.status != TaskStatus.DONE,
    )
    total_active_tasks = (await db.execute(active_tasks_stmt)).scalar() or 0

    # Query members with task counts
    stmt = (
        select(
            User.id,
            User.name,
            User.email,
            User.avatar_url,
            OrganizationMember.role,
            func.count(Task.id).label("assigned_tasks"),
            func.count(case((Task.status == TaskStatus.DONE, Task.id))).label("completed_tasks"),
            func.count(case((Task.status != TaskStatus.DONE, Task.id))).label("pending_tasks"),
            func.count(
                case(((Task.status != TaskStatus.DONE) & (Task.due_date < today), Task.id))
            ).label("overdue_tasks"),
        )
        .select_from(OrganizationMember)
        .join(User, User.id == OrganizationMember.user_id)
        .outerjoin(
            Task,
            (Task.assignee_id == User.id) & (Task.organization_id == org_id),
        )
        .where(OrganizationMember.organization_id == org_id)
        .group_by(User.id, User.name, User.email, User.avatar_url, OrganizationMember.role)
        .order_by(OrganizationMember.joined_at.asc())
    )
    rows = (await db.execute(stmt)).all()

    members_stats: List[MemberWorkloadStatItem] = []
    for uid, name, email, avatar, role, assigned, comp, pend, overdue in rows:
        pending_count = pend or 0
        workload_pct = (
            round((pending_count / total_active_tasks * 100), 1)
            if total_active_tasks > 0
            else 0.0
        )
        members_stats.append(
            MemberWorkloadStatItem(
                user_id=uid,
                name=name or email,
                email=email,
                avatar_url=avatar,
                role=role.value if role else None,
                assigned_tasks_count=assigned or 0,
                completed_tasks_count=comp or 0,
                pending_tasks_count=pending_count,
                overdue_tasks_count=overdue or 0,
                workload_percentage=workload_pct,
            )
        )

    return TeamStatsResponse(
        total_members=len(members_stats),
        active_tasks_count=total_active_tasks,
        members=members_stats,
    )


# ---------------------------------------------------------------------------
# 5. Recent Activity
# ---------------------------------------------------------------------------

@router.get(
    "/dashboard/recent-activity",
    response_model=ActivityListResponse,
    summary="Get Workspace Recent Activity",
    description="Returns recent audit events for the workspace dashboard feed.",
)
async def get_dashboard_recent_activity(
    limit: int = Query(10, ge=1, le=50, description="Items to return"),
    offset: int = Query(0, ge=0, description="Page offset"),
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> ActivityListResponse:
    org_id = ctx.organization_id

    count_stmt = select(func.count(Activity.id)).where(Activity.organization_id == org_id)
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = (
        select(Activity)
        .options(selectinload(Activity.user))
        .where(Activity.organization_id == org_id)
        .order_by(Activity.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    activities = (await db.execute(stmt)).scalars().all()

    from app.routes.activities import serialize_activity

    return ActivityListResponse(
        items=[serialize_activity(a) for a in activities],
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# 6. Project Analytics Deep Dive
# ---------------------------------------------------------------------------

@router.get(
    "/projects/{project_id}/analytics",
    response_model=ProjectAnalyticsResponse,
    summary="Get Project Analytics",
    description="Retrieves deep analytics for a specific project including progress, task distribution, and deadlines.",
)
async def get_project_analytics(
    project_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> ProjectAnalyticsResponse:
    org_id = ctx.organization_id
    today = date.today()

    proj = await db.scalar(
        select(Project).where(Project.id == project_id, Project.organization_id == org_id)
    )
    if not proj:
        raise NotFoundException(f"Project '{project_id}' not found.", code="PROJECT_NOT_FOUND")

    # Aggregate task stats for project
    stmt = select(
        func.count(Task.id).label("total"),
        func.count(case((Task.status == TaskStatus.DONE, Task.id))).label("completed"),
        func.count(case((Task.status != TaskStatus.DONE, Task.id))).label("pending"),
        func.count(
            case(((Task.status != TaskStatus.DONE) & (Task.due_date < today), Task.id))
        ).label("overdue"),
        func.coalesce(func.sum(Task.estimated_hours), 0).label("est_hours"),
        func.coalesce(func.sum(Task.actual_hours), 0).label("act_hours"),
    ).where(Task.project_id == project_id, Task.organization_id == org_id)
    agg = (await db.execute(stmt)).one()

    total_t = agg.total or 0
    completed_t = agg.completed or 0
    completion_pct = round((completed_t / total_t * 100), 2) if total_t > 0 else float(proj.progress)

    # Status distribution
    status_stmt = (
        select(Task.status, func.count(Task.id))
        .where(Task.project_id == project_id, Task.organization_id == org_id)
        .group_by(Task.status)
    )
    status_rows = (await db.execute(status_stmt)).all()
    tasks_by_status = {s.value: 0 for s in TaskStatus}
    for st, count in status_rows:
        tasks_by_status[st.value] = count

    # Priority distribution
    priority_stmt = (
        select(Task.priority, func.count(Task.id))
        .where(Task.project_id == project_id, Task.organization_id == org_id)
        .group_by(Task.priority)
    )
    priority_rows = (await db.execute(priority_stmt)).all()
    tasks_by_priority = {p.value: 0 for p in PriorityLevel}
    for pr, count in priority_rows:
        tasks_by_priority[pr.value] = count

    days_remaining: Optional[int] = None
    is_overdue = False
    if proj.due_date:
        days_remaining = (proj.due_date - today).days
        is_overdue = bool(proj.due_date < today and proj.status != ProjectStatus.COMPLETED)

    return ProjectAnalyticsResponse(
        project_id=proj.id,
        project_name=proj.name,
        project_key=proj.key,
        status=proj.status,
        priority=proj.priority,
        completion_percentage=completion_pct,
        tasks_by_status=tasks_by_status,
        tasks_by_priority=tasks_by_priority,
        total_tasks=total_t,
        completed_tasks=completed_t,
        pending_tasks=agg.pending or 0,
        overdue_tasks_count=agg.overdue or 0,
        start_date=proj.start_date,
        due_date=proj.due_date,
        days_remaining=days_remaining,
        is_overdue=is_overdue,
        estimated_hours_total=float(agg.est_hours or 0.0),
        actual_hours_total=float(agg.act_hours or 0.0),
    )


# ---------------------------------------------------------------------------
# 7. Team Analytics Deep Dive
# ---------------------------------------------------------------------------

@router.get(
    "/teams/{team_id}/analytics",
    response_model=TeamAnalyticsResponse,
    summary="Get Team Analytics",
    description="Retrieves workload distribution and execution metrics for members of a specific team.",
)
async def get_team_analytics(
    team_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> TeamAnalyticsResponse:
    org_id = ctx.organization_id
    today = date.today()

    team = await db.scalar(
        select(Team).where(Team.id == team_id, Team.organization_id == org_id)
    )
    if not team:
        raise NotFoundException(f"Team '{team_id}' not found.", code="TEAM_NOT_FOUND")

    # Total active tasks assigned to this team's members
    team_active_tasks_stmt = (
        select(func.count(Task.id))
        .join(TeamMember, TeamMember.user_id == Task.assignee_id)
        .where(
            TeamMember.team_id == team_id,
            Task.organization_id == org_id,
            Task.status != TaskStatus.DONE,
        )
    )
    total_team_active_tasks = (await db.execute(team_active_tasks_stmt)).scalar() or 0

    # Query members of this team and their task metrics
    stmt = (
        select(
            User.id,
            User.name,
            User.email,
            User.avatar_url,
            OrganizationMember.role,
            func.count(Task.id).label("assigned"),
            func.count(case((Task.status == TaskStatus.DONE, Task.id))).label("completed"),
            func.count(case((Task.status != TaskStatus.DONE, Task.id))).label("pending"),
            func.count(
                case(((Task.status != TaskStatus.DONE) & (Task.due_date < today), Task.id))
            ).label("overdue"),
        )
        .select_from(TeamMember)
        .join(User, User.id == TeamMember.user_id)
        .join(
            OrganizationMember,
            (OrganizationMember.user_id == User.id) & (OrganizationMember.organization_id == org_id),
        )
        .outerjoin(
            Task,
            (Task.assignee_id == User.id) & (Task.organization_id == org_id),
        )
        .where(TeamMember.team_id == team_id)
        .group_by(User.id, User.name, User.email, User.avatar_url, OrganizationMember.role)
        .order_by(TeamMember.joined_at.asc())
    )
    rows = (await db.execute(stmt)).all()

    members_stats: List[MemberWorkloadStatItem] = []
    for uid, name, email, avatar, role, assigned, comp, pend, overdue in rows:
        pending_count = pend or 0
        workload_pct = (
            round((pending_count / total_team_active_tasks * 100), 1)
            if total_team_active_tasks > 0
            else 0.0
        )
        members_stats.append(
            MemberWorkloadStatItem(
                user_id=uid,
                name=name or email,
                email=email,
                avatar_url=avatar,
                role=role.value if role else None,
                assigned_tasks_count=assigned or 0,
                completed_tasks_count=comp or 0,
                pending_tasks_count=pending_count,
                overdue_tasks_count=overdue or 0,
                workload_percentage=workload_pct,
            )
        )

    return TeamAnalyticsResponse(
        team_id=team.id,
        team_name=team.name,
        member_count=len(members_stats),
        members=members_stats,
    )
