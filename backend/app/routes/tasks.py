import logging
import uuid
from typing import Dict, List, Optional

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
from app.models.enums import NotificationType, PriorityLevel, TaskStatus, UserRole
from app.models.organization import OrganizationMember
from app.models.project import Project
from app.models.task import Label, Subtask, Task, task_labels
from app.models.user import User
from app.schemas.auth import UserProfileResponse
from app.schemas.task import (
    KanbanBoardResponse,
    KanbanColumnResponse,
    LabelResponse,
    SubtaskCreateRequest,
    SubtaskResponse,
    SubtaskUpdateRequest,
    TaskCreateRequest,
    TaskPositionUpdateRequest,
    TaskResponse,
    TaskStatusUpdateRequest,
    TaskUpdateRequest,
)
from app.services.activity import record_activity
from app.services.notification import create_notification

logger = logging.getLogger("flowstate.routes.tasks")

router = APIRouter(tags=["Tasks & Kanban"])


async def get_task_in_org(
    task_id: uuid.UUID,
    org_id: uuid.UUID,
    db: AsyncSession,
) -> Task:
    """Helper verifying that a task exists and belongs to the caller's tenant organization."""
    stmt = (
        select(Task)
        .options(
            selectinload(Task.assignee),
            selectinload(Task.creator),
            selectinload(Task.labels),
            selectinload(Task.subtasks),
        )
        .where(Task.id == task_id, Task.organization_id == org_id)
    )
    task = (await db.execute(stmt)).scalar_one_or_none()
    if not task:
        raise NotFoundException(
            f"Task '{task_id}' not found in organization '{org_id}'.",
            code="TASK_NOT_FOUND",
        )
    return task


def can_edit_task(ctx: ActiveOrganizationContext, task: Task) -> bool:
    """Allows edit if caller is Owner, Admin, Manager, the Task Creator, or the Task Assignee."""
    if ctx.has_min_role(UserRole.MANAGER):
        return True
    if task.creator_id is not None and task.creator_id == ctx.user_id:
        return True
    if task.assignee_id is not None and task.assignee_id == ctx.user_id:
        return True
    return False


def can_delete_task(ctx: ActiveOrganizationContext, task: Task) -> bool:
    """Allows deletion if caller is Owner, Admin, Manager, or the Task Creator."""
    if ctx.has_min_role(UserRole.MANAGER):
        return True
    if task.creator_id is not None and task.creator_id == ctx.user_id:
        return True
    return False


def serialize_task(task: Task) -> TaskResponse:
    """Serializes a Task ORM instance into TaskResponse with subtask metrics."""
    subtasks = task.subtasks or []
    labels = task.labels or []
    subtasks_count = len(subtasks)
    subtasks_completed = sum(1 for st in subtasks if st.completed)

    return TaskResponse(
        id=task.id,
        organization_id=task.organization_id,
        project_id=task.project_id,
        task_number=task.task_number,
        key=task.key,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        assignee_id=task.assignee_id,
        assignee=UserProfileResponse.model_validate(task.assignee) if (task.assignee_id and task.assignee) else None,
        creator_id=task.creator_id,
        creator=UserProfileResponse.model_validate(task.creator) if task.creator else None,
        start_date=task.start_date,
        due_date=task.due_date,
        estimated_hours=task.estimated_hours,
        actual_hours=task.actual_hours,
        order=task.order,
        labels=[
            LabelResponse(
                id=lbl.id,
                organization_id=lbl.organization_id,
                name=lbl.name,
                color=lbl.color,
                created_at=lbl.created_at,
            )
            for lbl in labels
        ],
        subtasks=[
            SubtaskResponse(
                id=st.id,
                task_id=st.task_id,
                title=st.title,
                completed=st.completed,
                order=st.order,
                created_at=st.created_at,
                updated_at=st.updated_at,
            )
            for st in sorted(subtasks, key=lambda s: s.order)
        ],
        subtasks_count=subtasks_count,
        subtasks_completed_count=subtasks_completed,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


# ---------------------------------------------------------------------------
# 1. Task CRUD Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Task",
    description="Creates a work item in the project using atomic counter task numbering (e.g. FLW-101).",
)
async def create_task(
    project_id: uuid.UUID,
    payload: TaskCreateRequest,
    ctx: ActiveOrganizationContext = Depends(require_min_org_role(UserRole.DESIGNER)),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    org_id = ctx.organization_id

    # 1. Acquire row-level exclusive lock on Project to guarantee atomic, concurrency-safe task numbering
    proj_stmt = (
        select(Project)
        .where(Project.id == project_id, Project.organization_id == org_id)
        .with_for_update()
    )
    project = (await db.execute(proj_stmt)).scalar_one_or_none()
    if not project:
        raise NotFoundException(
            f"Project '{project_id}' not found in this organization.",
            code="PROJECT_NOT_FOUND",
        )

    # 2. Concurrency-safe atomic counter increment
    project.last_task_number += 1
    task_number = project.last_task_number
    task_key = f"{project.key}-{task_number}"

    # 3. Validate Assignee (must belong to the active organization)
    assignee_user: Optional[User] = None
    if payload.assignee_id:
        is_org_member = await db.scalar(
            select(OrganizationMember.id).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == payload.assignee_id,
            )
        )
        if not is_org_member:
            raise BadRequestException(
                "Task assignee must be an active member of this organization.",
                code="INVALID_TASK_ASSIGNEE",
            )
        assignee_user = await db.scalar(select(User).where(User.id == payload.assignee_id))

    # 4. Resolve Order Position within Column
    if payload.order is not None:
        task_order = float(payload.order)
    else:
        max_order = await db.scalar(
            select(func.max(Task.order)).where(
                Task.project_id == project_id,
                Task.status == payload.status,
            )
        )
        task_order = (float(max_order) + 1000.0) if max_order is not None else 1000.0

    # 5. Create Task
    task = Task(
        organization_id=org_id,
        project_id=project_id,
        task_number=task_number,
        key=task_key,
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description else "",
        status=payload.status,
        priority=payload.priority,
        assignee_id=payload.assignee_id,
        creator_id=ctx.user_id,
        start_date=payload.start_date,
        due_date=payload.due_date,
        estimated_hours=payload.estimated_hours,
        actual_hours=payload.actual_hours,
        order=task_order,
    )
    db.add(task)
    await db.flush()

    # 6. Associate initial labels if provided
    labels_to_attach: List[Label] = []
    if payload.label_ids:
        label_stmt = select(Label).where(
            Label.id.in_(payload.label_ids),
            Label.organization_id == org_id,
        )
        labels_to_attach = list((await db.execute(label_stmt)).scalars().all())
        for lbl in labels_to_attach:
            await db.execute(task_labels.insert().values(task_id=task.id, label_id=lbl.id))

    # 7. Record activity and dispatch assignment notification
    await record_activity(
        db=db,
        organization_id=org_id,
        user_id=ctx.user_id,
        action="task_created",
        target_type="task",
        target_id=task.id,
        target_title=task.title,
        project_id=project_id,
        details={"task_key": task_key, "priority": task.priority.value, "status": task.status.value},
    )

    if payload.assignee_id and payload.assignee_id != ctx.user_id:
        await create_notification(
            db=db,
            user_id=payload.assignee_id,
            sender_id=ctx.user_id,
            type=NotificationType.ASSIGNMENT,
            title=f"Assigned to {task_key}",
            message=f"You have been assigned to task {task_key}: {task.title}",
            link=f"/tasks/{task.id}",
        )

    await db.commit()

    # Reload full task
    full_task = await get_task_in_org(task.id, org_id, db)
    return serialize_task(full_task)


@router.get(
    "/projects/{project_id}/tasks",
    response_model=List[TaskResponse],
    summary="List Project Tasks",
    description="Lists all tasks in a project with optional status, priority, and assignee filters.",
)
async def list_project_tasks(
    project_id: uuid.UUID,
    task_status: Optional[TaskStatus] = Query(None, alias="status"),
    priority: Optional[PriorityLevel] = Query(None),
    assignee_id: Optional[uuid.UUID] = Query(None),
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> List[TaskResponse]:
    org_id = ctx.organization_id

    # Verify project exists in org
    proj_exists = await db.scalar(
        select(Project.id).where(Project.id == project_id, Project.organization_id == org_id)
    )
    if not proj_exists:
        raise NotFoundException(f"Project '{project_id}' not found.", code="PROJECT_NOT_FOUND")

    stmt = (
        select(Task)
        .options(
            selectinload(Task.assignee),
            selectinload(Task.creator),
            selectinload(Task.labels),
            selectinload(Task.subtasks),
        )
        .where(Task.project_id == project_id, Task.organization_id == org_id)
    )
    if task_status:
        stmt = stmt.where(Task.status == task_status)
    if priority:
        stmt = stmt.where(Task.priority == priority)
    if assignee_id:
        stmt = stmt.where(Task.assignee_id == assignee_id)

    stmt = stmt.order_by(Task.order.asc(), Task.created_at.asc())
    tasks = (await db.execute(stmt)).scalars().all()

    return [serialize_task(t) for t in tasks]


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Get Task Details",
    description="Retrieves comprehensive task details, labels, and subtasks.",
)
async def get_task(
    task_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    task = await get_task_in_org(task_id, ctx.organization_id, db)
    return serialize_task(task)


@router.patch(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Update Task",
    description="Modifies task title, description, priority, dates, hours, order, or assignee.",
)
async def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdateRequest,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    task = await get_task_in_org(task_id, ctx.organization_id, db)

    # Authorization guard: must be Manager+, or task creator, or task assignee
    if not can_edit_task(ctx, task):
        raise ForbiddenException(
            "Access denied: You do not have permission to modify this task.",
            code="INSUFFICIENT_ROLE_PERMISSIONS",
        )

    old_assignee_id = task.assignee_id
    old_status = task.status
    assignment_changed = False
    status_changed = False

    # Handle unassign or new assignment
    if payload.unassign:
        if task.assignee_id is not None:
            assignment_changed = True
        task.assignee_id = None
        task.assignee = None
    elif payload.assignee_id is not None:
        if payload.assignee_id != task.assignee_id:
            is_org_member = await db.scalar(
                select(OrganizationMember.id).where(
                    OrganizationMember.organization_id == ctx.organization_id,
                    OrganizationMember.user_id == payload.assignee_id,
                )
            )
            if not is_org_member:
                raise BadRequestException(
                    "Task assignee must be an active member of this organization.",
                    code="INVALID_TASK_ASSIGNEE",
                )
            task.assignee_id = payload.assignee_id
            assignment_changed = True

    if payload.title is not None:
        task.title = payload.title.strip()
    if payload.description is not None:
        task.description = payload.description.strip()
    if payload.status is not None:
        if payload.status != old_status:
            status_changed = True
        task.status = payload.status
    if payload.priority is not None:
        task.priority = payload.priority
    if payload.start_date is not None:
        task.start_date = payload.start_date
    if payload.due_date is not None:
        task.due_date = payload.due_date
    if payload.estimated_hours is not None:
        task.estimated_hours = payload.estimated_hours
    if payload.actual_hours is not None:
        task.actual_hours = payload.actual_hours
    if payload.order is not None:
        task.order = float(payload.order)

    # Record activity and notifications
    if assignment_changed:
        await record_activity(
            db=db,
            organization_id=ctx.organization_id,
            user_id=ctx.user_id,
            action="task_assigned",
            target_type="task",
            target_id=task.id,
            target_title=task.title,
            project_id=task.project_id,
            details={"task_key": task.key, "assignee_id": str(task.assignee_id) if task.assignee_id else None},
        )
        if task.assignee_id and task.assignee_id != ctx.user_id:
            await create_notification(
                db=db,
                user_id=task.assignee_id,
                sender_id=ctx.user_id,
                type=NotificationType.ASSIGNMENT,
                title=f"Assigned to {task.key}",
                message=f"You have been assigned to task {task.key}: {task.title}",
                link=f"/tasks/{task.id}",
            )
    elif status_changed:
        await record_activity(
            db=db,
            organization_id=ctx.organization_id,
            user_id=ctx.user_id,
            action="task_status_changed",
            target_type="task",
            target_id=task.id,
            target_title=task.title,
            project_id=task.project_id,
            details={"task_key": task.key, "old_status": old_status.value, "new_status": task.status.value},
        )
    else:
        await record_activity(
            db=db,
            organization_id=ctx.organization_id,
            user_id=ctx.user_id,
            action="task_updated",
            target_type="task",
            target_id=task.id,
            target_title=task.title,
            project_id=task.project_id,
            details={"task_key": task.key},
        )

    await db.commit()
    full_task = await get_task_in_org(task.id, ctx.organization_id, db)
    return serialize_task(full_task)


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Task",
    description="Deletes a task and all associated subtasks and label mappings. Requires Manager, Admin, Owner, or Task Creator.",
)
async def delete_task(
    task_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> dict:
    task = await get_task_in_org(task_id, ctx.organization_id, db)

    if not can_delete_task(ctx, task):
        raise ForbiddenException(
            "Access denied: Deleting tasks requires Manager, Admin, Owner, or Task Creator status.",
            code="INSUFFICIENT_ROLE_PERMISSIONS",
        )

    task_key = task.key
    await record_activity(
        db=db,
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        action="task_deleted",
        target_type="task",
        target_id=task.id,
        target_title=task.title,
        project_id=task.project_id,
        details={"task_key": task_key},
    )

    await db.delete(task)
    await db.commit()

    return {
        "status": "success",
        "message": f"Task '{task_key}' was successfully deleted.",
        "task_id": str(task_id),
    }


# ---------------------------------------------------------------------------
# 2. Kanban Board APIs
# ---------------------------------------------------------------------------

@router.get(
    "/projects/{project_id}/kanban",
    response_model=KanbanBoardResponse,
    summary="Get Kanban Board",
    description="Retrieves the full Kanban board for a project, grouped by status columns and sorted by order ASC.",
)
async def get_kanban_board(
    project_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> KanbanBoardResponse:
    org_id = ctx.organization_id

    proj_exists = await db.scalar(
        select(Project.id).where(Project.id == project_id, Project.organization_id == org_id)
    )
    if not proj_exists:
        raise NotFoundException(f"Project '{project_id}' not found.", code="PROJECT_NOT_FOUND")

    stmt = (
        select(Task)
        .options(
            selectinload(Task.assignee),
            selectinload(Task.creator),
            selectinload(Task.labels),
            selectinload(Task.subtasks),
        )
        .where(Task.project_id == project_id, Task.organization_id == org_id)
        .order_by(Task.order.asc(), Task.created_at.asc())
    )
    all_tasks = (await db.execute(stmt)).scalars().all()

    # Initialize buckets for standard columns
    columns_data: Dict[str, List[TaskResponse]] = {
        s.value: [] for s in TaskStatus
    }
    for t in all_tasks:
        serialized = serialize_task(t)
        if t.status.value in columns_data:
            columns_data[t.status.value].append(serialized)

    columns_response: Dict[str, KanbanColumnResponse] = {}
    for st in TaskStatus:
        bucket = columns_data[st.value]
        columns_response[st.value] = KanbanColumnResponse(
            status=st,
            tasks_count=len(bucket),
            tasks=bucket,
        )

    return KanbanBoardResponse(
        project_id=project_id,
        total_tasks=len(all_tasks),
        columns=columns_response,
    )


@router.patch(
    "/tasks/{task_id}/status",
    response_model=TaskResponse,
    summary="Update Task Status (Kanban Transition)",
    description="Transitions a task to a different Kanban status column.",
)
async def update_task_status(
    task_id: uuid.UUID,
    payload: TaskStatusUpdateRequest,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    task = await get_task_in_org(task_id, ctx.organization_id, db)

    if not can_edit_task(ctx, task):
        raise ForbiddenException(
            "Access denied: You do not have permission to transition this task.",
            code="INSUFFICIENT_ROLE_PERMISSIONS",
        )

    old_status = task.status
    task.status = payload.status

    if payload.status != old_status:
        await record_activity(
            db=db,
            organization_id=ctx.organization_id,
            user_id=ctx.user_id,
            action="task_status_changed",
            target_type="task",
            target_id=task.id,
            target_title=task.title,
            project_id=task.project_id,
            details={"task_key": task.key, "old_status": old_status.value, "new_status": payload.status.value},
        )

    await db.commit()

    full_task = await get_task_in_org(task.id, ctx.organization_id, db)
    return serialize_task(full_task)


@router.patch(
    "/tasks/{task_id}/position",
    response_model=TaskResponse,
    summary="Update Task Position (Kanban Reorder)",
    description="Reorders a task within a column or moves it between columns using fractional ordering.",
)
async def update_task_position(
    task_id: uuid.UUID,
    payload: TaskPositionUpdateRequest,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    task = await get_task_in_org(task_id, ctx.organization_id, db)

    if not can_edit_task(ctx, task):
        raise ForbiddenException(
            "Access denied: You do not have permission to move this task.",
            code="INSUFFICIENT_ROLE_PERMISSIONS",
        )

    # 1. Update column if status changed
    if payload.status is not None:
        task.status = payload.status

    # 2. Fractional ordering calculation
    if payload.order is not None:
        task.order = float(payload.order)
    elif payload.before_task_id or payload.after_task_id:
        order_before: Optional[float] = None
        order_after: Optional[float] = None

        if payload.before_task_id:
            order_before = await db.scalar(
                select(Task.order).where(Task.id == payload.before_task_id, Task.organization_id == ctx.organization_id)
            )
        if payload.after_task_id:
            order_after = await db.scalar(
                select(Task.order).where(Task.id == payload.after_task_id, Task.organization_id == ctx.organization_id)
            )

        if order_before is not None and order_after is not None:
            task.order = (float(order_before) + float(order_after)) / 2.0
        elif order_before is not None:
            val = float(order_before)
            task.order = val / 2.0 if val > 1.0 else val - 1000.0
        elif order_after is not None:
            task.order = float(order_after) + 1000.0

    await db.commit()
    full_task = await get_task_in_org(task.id, ctx.organization_id, db)
    return serialize_task(full_task)


# ---------------------------------------------------------------------------
# 3. Subtask Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/tasks/{task_id}/subtasks",
    response_model=SubtaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Subtask",
    description="Adds a checklist item to a task.",
)
async def create_subtask(
    task_id: uuid.UUID,
    payload: SubtaskCreateRequest,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> SubtaskResponse:
    task = await get_task_in_org(task_id, ctx.organization_id, db)

    if not can_edit_task(ctx, task):
        raise ForbiddenException("Access denied: You cannot add checklist items to this task.", code="INSUFFICIENT_ROLE_PERMISSIONS")

    max_order = await db.scalar(select(func.max(Subtask.order)).where(Subtask.task_id == task_id))
    st_order = (max_order + 1) if max_order is not None else 0

    subtask = Subtask(
        task_id=task.id,
        title=payload.title.strip(),
        completed=payload.completed,
        order=st_order,
    )
    db.add(subtask)
    await db.commit()
    await db.refresh(subtask)

    return SubtaskResponse(
        id=subtask.id,
        task_id=subtask.task_id,
        title=subtask.title,
        completed=subtask.completed,
        order=subtask.order,
        created_at=subtask.created_at,
        updated_at=subtask.updated_at,
    )


@router.get(
    "/tasks/{task_id}/subtasks",
    response_model=List[SubtaskResponse],
    summary="List Subtasks",
    description="Lists all checklist items for a task ordered by order ASC.",
)
async def list_subtasks(
    task_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> List[SubtaskResponse]:
    await get_task_in_org(task_id, ctx.organization_id, db)

    stmt = select(Subtask).where(Subtask.task_id == task_id).order_by(Subtask.order.asc())
    subtasks = (await db.execute(stmt)).scalars().all()

    return [
        SubtaskResponse(
            id=st.id,
            task_id=st.task_id,
            title=st.title,
            completed=st.completed,
            order=st.order,
            created_at=st.created_at,
            updated_at=st.updated_at,
        )
        for st in subtasks
    ]


@router.patch(
    "/tasks/{task_id}/subtasks/{subtask_id}",
    response_model=SubtaskResponse,
    summary="Update Subtask (Task Path)",
)
@router.patch(
    "/subtasks/{subtask_id}",
    response_model=SubtaskResponse,
    summary="Update Subtask",
    description="Modifies a checklist item title, completion state, or order.",
)
async def update_subtask(
    subtask_id: uuid.UUID,
    payload: SubtaskUpdateRequest,
    task_id: Optional[uuid.UUID] = None,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> SubtaskResponse:
    # Query subtask and its parent task with tenant verification
    stmt = (
        select(Subtask)
        .join(Task, Task.id == Subtask.task_id)
        .where(Subtask.id == subtask_id, Task.organization_id == ctx.organization_id)
    )
    subtask = (await db.execute(stmt)).scalar_one_or_none()
    if not subtask:
        raise NotFoundException(f"Subtask '{subtask_id}' not found.", code="SUBTASK_NOT_FOUND")

    task = await db.scalar(select(Task).where(Task.id == subtask.task_id))
    if not can_edit_task(ctx, task):
        raise ForbiddenException("Access denied: You cannot modify checklist items on this task.", code="INSUFFICIENT_ROLE_PERMISSIONS")

    if payload.title is not None:
        subtask.title = payload.title.strip()
    if payload.completed is not None:
        subtask.completed = payload.completed
    if payload.order is not None:
        subtask.order = payload.order

    await db.commit()
    await db.refresh(subtask)

    return SubtaskResponse(
        id=subtask.id,
        task_id=subtask.task_id,
        title=subtask.title,
        completed=subtask.completed,
        order=subtask.order,
        created_at=subtask.created_at,
        updated_at=subtask.updated_at,
    )


@router.delete(
    "/tasks/{task_id}/subtasks/{subtask_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Subtask (Task Path)",
)
@router.delete(
    "/subtasks/{subtask_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Subtask",
    description="Removes a checklist item from a task.",
)
async def delete_subtask(
    subtask_id: uuid.UUID,
    task_id: Optional[uuid.UUID] = None,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = (
        select(Subtask)
        .join(Task, Task.id == Subtask.task_id)
        .where(Subtask.id == subtask_id, Task.organization_id == ctx.organization_id)
    )
    subtask = (await db.execute(stmt)).scalar_one_or_none()
    if not subtask:
        raise NotFoundException(f"Subtask '{subtask_id}' not found.", code="SUBTASK_NOT_FOUND")

    task = await db.scalar(select(Task).where(Task.id == subtask.task_id))
    if not can_edit_task(ctx, task):
        raise ForbiddenException("Access denied: You cannot delete checklist items on this task.", code="INSUFFICIENT_ROLE_PERMISSIONS")

    await db.delete(subtask)
    await db.commit()

    return {
        "status": "success",
        "message": f"Subtask '{subtask_id}' was successfully deleted.",
        "subtask_id": str(subtask_id),
    }


# ---------------------------------------------------------------------------
# 4. Task Labels Attachment Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/tasks/{task_id}/labels/{label_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Attach Label to Task",
    description="Associates an organization label with a task.",
)
async def attach_label_to_task(
    task_id: uuid.UUID,
    label_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    task = await get_task_in_org(task_id, ctx.organization_id, db)

    if not can_edit_task(ctx, task):
        raise ForbiddenException("Access denied: You cannot attach labels to this task.", code="INSUFFICIENT_ROLE_PERMISSIONS")

    # Verify label exists and belongs to the same organization
    label = await db.scalar(
        select(Label).where(Label.id == label_id, Label.organization_id == ctx.organization_id)
    )
    if not label:
        raise NotFoundException(f"Label '{label_id}' not found in this organization.", code="LABEL_NOT_FOUND")

    # Check if already attached
    attached_ids = {lbl.id for lbl in task.labels}
    if label.id not in attached_ids:
        task.labels.append(label)
        await db.commit()

    full_task = await get_task_in_org(task.id, ctx.organization_id, db)
    return serialize_task(full_task)


@router.delete(
    "/tasks/{task_id}/labels/{label_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove Label from Task",
    description="Detaches a label from a task.",
)
async def remove_label_from_task(
    task_id: uuid.UUID,
    label_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    task = await get_task_in_org(task_id, ctx.organization_id, db)

    if not can_edit_task(ctx, task):
        raise ForbiddenException("Access denied: You cannot remove labels from this task.", code="INSUFFICIENT_ROLE_PERMISSIONS")

    task.labels = [lbl for lbl in task.labels if lbl.id != label_id]
    await db.commit()

    full_task = await get_task_in_org(task.id, ctx.organization_id, db)
    return serialize_task(full_task)
