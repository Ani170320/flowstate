import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ForbiddenException, NotFoundException
from app.dependencies.auth import (
    ActiveOrganizationContext,
    get_active_organization,
)
from app.dependencies.database import get_db
from app.models.collaboration import Activity
from app.models.project import Project
from app.models.task import Task
from app.schemas.auth import UserProfileResponse
from app.schemas.collaboration import (
    ActivityListResponse,
    ActivityResponse,
)

logger = logging.getLogger("flowstate.routes.activities")

router = APIRouter(tags=["Activity Audit Trail"])


def serialize_activity(act: Activity) -> ActivityResponse:
    """Converts Activity ORM model to ActivityResponse."""
    return ActivityResponse(
        id=act.id,
        organization_id=act.organization_id,
        user_id=act.user_id,
        user=UserProfileResponse.model_validate(act.user) if act.user else None,
        action=act.action,
        target_type=act.target_type,
        target_id=act.target_id,
        target_title=act.target_title,
        project_id=act.project_id,
        details=act.details or {},
        created_at=act.created_at,
    )


# ---------------------------------------------------------------------------
# Activity Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/organizations/{org_id}/activities",
    response_model=ActivityListResponse,
    summary="List Organization Activities",
    description="Retrieves a paginated audit timeline for an entire organization ordered by created_at DESC.",
)
async def list_organization_activities(
    org_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Page offset"),
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> ActivityListResponse:
    if ctx.organization_id != org_id:
        raise ForbiddenException(
            "Access denied: You cannot view activities for another organization.",
            code="CROSS_ORGANIZATION_ACCESS_DENIED",
        )

    # Count total
    count_stmt = select(func.count(Activity.id)).where(Activity.organization_id == org_id)
    total = (await db.execute(count_stmt)).scalar() or 0

    # Query paginated activities
    stmt = (
        select(Activity)
        .options(selectinload(Activity.user))
        .where(Activity.organization_id == org_id)
        .order_by(Activity.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    activities = (await db.execute(stmt)).scalars().all()

    return ActivityListResponse(
        items=[serialize_activity(a) for a in activities],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/projects/{project_id}/activities",
    response_model=ActivityListResponse,
    summary="List Project Activities",
    description="Retrieves a paginated audit timeline for a project ordered by created_at DESC.",
)
async def list_project_activities(
    project_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Page offset"),
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> ActivityListResponse:
    proj = await db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.organization_id == ctx.organization_id,
        )
    )
    if not proj:
        raise NotFoundException(
            f"Project '{project_id}' not found in active organization.",
            code="PROJECT_NOT_FOUND",
        )

    count_stmt = select(func.count(Activity.id)).where(
        Activity.project_id == project_id,
        Activity.organization_id == ctx.organization_id,
    )
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = (
        select(Activity)
        .options(selectinload(Activity.user))
        .where(
            Activity.project_id == project_id,
            Activity.organization_id == ctx.organization_id,
        )
        .order_by(Activity.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    activities = (await db.execute(stmt)).scalars().all()

    return ActivityListResponse(
        items=[serialize_activity(a) for a in activities],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/tasks/{task_id}/activities",
    response_model=ActivityListResponse,
    summary="List Task Activities",
    description="Retrieves a paginated audit timeline for a task ordered by created_at DESC.",
)
async def list_task_activities(
    task_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Page offset"),
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> ActivityListResponse:
    task = await db.scalar(
        select(Task).where(
            Task.id == task_id,
            Task.organization_id == ctx.organization_id,
        )
    )
    if not task:
        raise NotFoundException(
            f"Task '{task_id}' not found in active organization.",
            code="TASK_NOT_FOUND",
        )

    count_stmt = select(func.count(Activity.id)).where(
        Activity.target_id == task_id,
        Activity.organization_id == ctx.organization_id,
    )
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = (
        select(Activity)
        .options(selectinload(Activity.user))
        .where(
            Activity.target_id == task_id,
            Activity.organization_id == ctx.organization_id,
        )
        .order_by(Activity.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    activities = (await db.execute(stmt)).scalars().all()

    return ActivityListResponse(
        items=[serialize_activity(a) for a in activities],
        total=total,
        limit=limit,
        offset=offset,
    )
