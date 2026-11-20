import logging
import uuid
from datetime import date, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies.auth import (
    ActiveOrganizationContext,
    get_active_organization,
)
from app.dependencies.database import get_db
from app.models.enums import PriorityLevel, ProjectStatus, TaskStatus
from app.models.project import Project
from app.models.task import Task
from app.schemas.auth import UserProfileResponse
from app.schemas.calendar import (
    CalendarDayResponse,
    CalendarEventResponse,
    CalendarUpcomingItemResponse,
    CalendarViewResponse,
)

logger = logging.getLogger("flowstate.routes.calendar")

router = APIRouter(prefix="/calendar", tags=["Calendar"])


def compute_date_window(
    view: str,
    reference_date: date,
    start_date: Optional[date],
    end_date: Optional[date],
) -> tuple[date, date]:
    """Computes start and end bounds based on view mode ('month', 'week', 'day') or explicit parameters."""
    if start_date and end_date:
        return start_date, end_date

    ref = reference_date or date.today()

    if view == "day":
        return ref, ref
    elif view == "week":
        # Monday to Sunday
        start = ref - timedelta(days=ref.weekday())
        end = start + timedelta(days=6)
        return start, end
    else:
        # Default: month view with boundary padding
        first_of_month = ref.replace(day=1)
        next_month = (first_of_month + timedelta(days=32)).replace(day=1)
        last_of_month = next_month - timedelta(days=1)
        # Pad to full calendar grid weeks (start on Monday, end on Sunday)
        start = first_of_month - timedelta(days=first_of_month.weekday())
        days_to_sunday = (6 - last_of_month.weekday()) % 7
        end = last_of_month + timedelta(days=days_to_sunday)
        return start, end


# ---------------------------------------------------------------------------
# Calendar Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=CalendarViewResponse,
    summary="Get Calendar View",
    description="Returns aggregated calendar events and daily buckets for month, week, or day view modes.",
)
async def get_calendar_view(
    view: str = Query("month", pattern="^(month|week|day)$", description="View mode"),
    reference_date: Optional[date] = Query(None, description="Center reference date"),
    start_date: Optional[date] = Query(None, description="Explicit start date"),
    end_date: Optional[date] = Query(None, description="Explicit end date"),
    project_id: Optional[uuid.UUID] = Query(None, description="Filter by project"),
    team_id: Optional[uuid.UUID] = Query(None, description="Filter by team"),
    assignee_id: Optional[uuid.UUID] = Query(None, description="Filter by task assignee"),
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> CalendarViewResponse:
    today = date.today()
    ref = reference_date or today
    win_start, win_end = compute_date_window(view, ref, start_date, end_date)

    # 1. Query Tasks in Date Window
    task_stmt = (
        select(Task)
        .join(Project, Project.id == Task.project_id)
        .options(selectinload(Task.assignee), selectinload(Task.project))
        .where(
            Task.organization_id == ctx.organization_id,
            or_(
                (Task.due_date >= win_start) & (Task.due_date <= win_end),
                (Task.start_date >= win_start) & (Task.start_date <= win_end),
            ),
        )
    )

    if project_id:
        task_stmt = task_stmt.where(Task.project_id == project_id)
    if team_id:
        task_stmt = task_stmt.where(Project.team_id == team_id)
    if assignee_id:
        task_stmt = task_stmt.where(Task.assignee_id == assignee_id)
    if status:
        task_stmt = task_stmt.where(Task.status == status)

    task_stmt = task_stmt.order_by(Task.due_date.asc().nulls_last())
    tasks = (await db.execute(task_stmt)).scalars().all()

    # 2. Query Project Milestones/Deadlines in Window
    proj_stmt = select(Project).where(
        Project.organization_id == ctx.organization_id,
        or_(
            (Project.due_date >= win_start) & (Project.due_date <= win_end),
            (Project.start_date >= win_start) & (Project.start_date <= win_end),
        ),
    )
    if project_id:
        proj_stmt = proj_stmt.where(Project.id == project_id)
    if team_id:
        proj_stmt = proj_stmt.where(Project.team_id == team_id)

    proj_stmt = proj_stmt.order_by(Project.due_date.asc().nulls_last())
    projects = (await db.execute(proj_stmt)).scalars().all()

    # 3. Transform to unified CalendarEventResponse
    events: List[CalendarEventResponse] = []

    for t in tasks:
        event_date = t.due_date or t.start_date or win_start
        is_overdue = bool(t.due_date and t.due_date < today and t.status != TaskStatus.DONE)
        events.append(
            CalendarEventResponse(
                id=f"task_{t.id}",
                entity_type="task",
                entity_id=t.id,
                title=t.title,
                key=t.key,
                start_date=t.start_date,
                due_date=t.due_date,
                date=event_date,
                status=t.status.value,
                priority=t.priority.value if t.priority else None,
                color=t.project.color if t.project else "#8B7CFF",
                project_id=t.project_id,
                project_name=t.project.name if t.project else None,
                assignee=UserProfileResponse.model_validate(t.assignee) if t.assignee else None,
                is_overdue=is_overdue,
            )
        )

    for p in projects:
        event_date = p.due_date or p.start_date or win_start
        is_overdue = bool(p.due_date and p.due_date < today and p.status != ProjectStatus.COMPLETED)
        events.append(
            CalendarEventResponse(
                id=f"project_{p.id}",
                entity_type="project",
                entity_id=p.id,
                title=f"Project: {p.name}",
                key=p.key,
                start_date=p.start_date,
                due_date=p.due_date,
                date=event_date,
                status=p.status.value,
                priority=p.priority.value if p.priority else None,
                color=p.color,
                project_id=p.id,
                project_name=p.name,
                assignee=None,
                is_overdue=is_overdue,
            )
        )

    # 4. Count Overdue Tasks across Workspace using SQL aggregation
    overdue_count_stmt = select(func.count(Task.id)).where(
        Task.organization_id == ctx.organization_id,
        Task.due_date < today,
        Task.status != TaskStatus.DONE,
    )
    if project_id:
        overdue_count_stmt = overdue_count_stmt.where(Task.project_id == project_id)
    if assignee_id:
        overdue_count_stmt = overdue_count_stmt.where(Task.assignee_id == assignee_id)

    overdue_tasks_count = (await db.execute(overdue_count_stmt)).scalar() or 0

    # 5. Group by Day
    day_map: Dict[date, List[CalendarEventResponse]] = {}
    curr = win_start
    while curr <= win_end:
        day_map[curr] = []
        curr += timedelta(days=1)

    for ev in events:
        if ev.date in day_map:
            day_map[ev.date].append(ev)

    days_list = [
        CalendarDayResponse(
            date=d,
            events_count=len(evs),
            events=evs,
        )
        for d, evs in sorted(day_map.items())
    ]

    return CalendarViewResponse(
        view=view,
        start_date=win_start,
        end_date=win_end,
        reference_date=ref,
        total_events=len(events),
        events=events,
        overdue_tasks_count=overdue_tasks_count,
        days=days_list,
    )


@router.get(
    "/events",
    response_model=List[CalendarEventResponse],
    summary="Get Calendar Events Flat List",
    description="Returns flat list of calendar events (tasks and project milestones) for timeline or calendar rendering.",
)
async def list_calendar_events(
    start_date: Optional[date] = Query(None, description="Start date bound"),
    end_date: Optional[date] = Query(None, description="End date bound"),
    project_id: Optional[uuid.UUID] = Query(None, description="Filter by project"),
    team_id: Optional[uuid.UUID] = Query(None, description="Filter by team"),
    assignee_id: Optional[uuid.UUID] = Query(None, description="Filter by assignee"),
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> List[CalendarEventResponse]:
    today = date.today()
    win_start = start_date or (today - timedelta(days=14))
    win_end = end_date or (today + timedelta(days=30))

    # Query Tasks
    task_stmt = (
        select(Task)
        .join(Project, Project.id == Task.project_id)
        .options(selectinload(Task.assignee), selectinload(Task.project))
        .where(
            Task.organization_id == ctx.organization_id,
            or_(
                (Task.due_date >= win_start) & (Task.due_date <= win_end),
                (Task.start_date >= win_start) & (Task.start_date <= win_end),
            ),
        )
    )
    if project_id:
        task_stmt = task_stmt.where(Task.project_id == project_id)
    if team_id:
        task_stmt = task_stmt.where(Project.team_id == team_id)
    if assignee_id:
        task_stmt = task_stmt.where(Task.assignee_id == assignee_id)
    if status:
        task_stmt = task_stmt.where(Task.status == status)

    tasks = (await db.execute(task_stmt.order_by(Task.due_date.asc().nulls_last()))).scalars().all()

    # Query Projects
    proj_stmt = select(Project).where(
        Project.organization_id == ctx.organization_id,
        or_(
            (Project.due_date >= win_start) & (Project.due_date <= win_end),
            (Project.start_date >= win_start) & (Project.start_date <= win_end),
        ),
    )
    if project_id:
        proj_stmt = proj_stmt.where(Project.id == project_id)
    if team_id:
        proj_stmt = proj_stmt.where(Project.team_id == team_id)

    projects = (await db.execute(proj_stmt.order_by(Project.due_date.asc().nulls_last()))).scalars().all()

    results: List[CalendarEventResponse] = []
    for t in tasks:
        ev_date = t.due_date or t.start_date or win_start
        is_overdue = bool(t.due_date and t.due_date < today and t.status != TaskStatus.DONE)
        results.append(
            CalendarEventResponse(
                id=f"task_{t.id}",
                entity_type="task",
                entity_id=t.id,
                title=t.title,
                key=t.key,
                start_date=t.start_date,
                due_date=t.due_date,
                date=ev_date,
                status=t.status.value,
                priority=t.priority.value if t.priority else None,
                color=t.project.color if t.project else "#8B7CFF",
                project_id=t.project_id,
                project_name=t.project.name if t.project else None,
                assignee=UserProfileResponse.model_validate(t.assignee) if t.assignee else None,
                is_overdue=is_overdue,
            )
        )

    for p in projects:
        ev_date = p.due_date or p.start_date or win_start
        is_overdue = bool(p.due_date and p.due_date < today and p.status != ProjectStatus.COMPLETED)
        results.append(
            CalendarEventResponse(
                id=f"project_{p.id}",
                entity_type="project",
                entity_id=p.id,
                title=f"Project: {p.name}",
                key=p.key,
                start_date=p.start_date,
                due_date=p.due_date,
                date=ev_date,
                status=p.status.value,
                priority=p.priority.value if p.priority else None,
                color=p.color,
                project_id=p.id,
                project_name=p.name,
                assignee=None,
                is_overdue=is_overdue,
            )
        )

    results.sort(key=lambda e: e.date)
    return results


@router.get(
    "/upcoming",
    response_model=List[CalendarUpcomingItemResponse],
    summary="Get Upcoming Deadlines",
    description="Returns tasks and project deadlines due within the next N days sorted by urgency.",
)
async def get_upcoming_deadlines(
    days: int = Query(14, ge=1, le=90, description="Horizon in days"),
    project_id: Optional[uuid.UUID] = Query(None, description="Filter by project"),
    team_id: Optional[uuid.UUID] = Query(None, description="Filter by team"),
    assignee_id: Optional[uuid.UUID] = Query(None, description="Filter by assignee"),
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> List[CalendarUpcomingItemResponse]:
    today = date.today()
    deadline_cutoff = today + timedelta(days=days)

    task_stmt = (
        select(Task)
        .join(Project, Project.id == Task.project_id)
        .options(selectinload(Task.assignee), selectinload(Task.project))
        .where(
            Task.organization_id == ctx.organization_id,
            Task.due_date.is_not(None),
            Task.due_date <= deadline_cutoff,
            Task.status != TaskStatus.DONE,
        )
    )

    if project_id:
        task_stmt = task_stmt.where(Task.project_id == project_id)
    if team_id:
        task_stmt = task_stmt.where(Project.team_id == team_id)
    if assignee_id:
        task_stmt = task_stmt.where(Task.assignee_id == assignee_id)

    task_stmt = task_stmt.order_by(Task.due_date.asc())
    tasks = (await db.execute(task_stmt)).scalars().all()

    items: List[CalendarUpcomingItemResponse] = []
    for t in tasks:
        if t.due_date is None:
            continue
        days_rem = (t.due_date - today).days
        items.append(
            CalendarUpcomingItemResponse(
                id=t.id,
                entity_type="task",
                key=t.key,
                title=t.title,
                project_name=t.project.name if t.project else None,
                due_date=t.due_date,
                days_remaining=days_rem,
                is_overdue=days_rem < 0,
                priority=t.priority.value,
                status=t.status.value,
                assignee=UserProfileResponse.model_validate(t.assignee) if t.assignee else None,
            )
        )

    return items
