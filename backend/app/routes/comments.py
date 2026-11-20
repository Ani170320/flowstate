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
from app.models.collaboration import Comment
from app.models.enums import NotificationType, UserRole
from app.models.task import Task
from app.schemas.auth import UserProfileResponse
from app.schemas.collaboration import (
    CommentCreateRequest,
    CommentListResponse,
    CommentResponse,
    CommentUpdateRequest,
)
from app.services.activity import record_activity
from app.services.notification import create_notification

logger = logging.getLogger("flowstate.routes.comments")

router = APIRouter(tags=["Comments"])


def can_manage_comment(ctx: ActiveOrganizationContext, comment: Comment) -> bool:
    """Allows update or deletion if caller is the comment author, or organization Manager, Admin, or Owner."""
    if ctx.has_min_role(UserRole.MANAGER):
        return True
    if comment.author_id is not None and comment.author_id == ctx.user_id:
        return True
    return False


def serialize_comment(comment: Comment) -> CommentResponse:
    """Transforms Comment ORM model to serialized CommentResponse."""
    return CommentResponse(
        id=comment.id,
        task_id=comment.task_id,
        author_id=comment.author_id,
        author=UserProfileResponse.model_validate(comment.author) if comment.author else None,
        content=comment.content,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


# ---------------------------------------------------------------------------
# Comments Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/tasks/{task_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Comment to Task",
    description="Posts a markdown discussion comment on a task within the tenant organization.",
)
async def create_comment(
    task_id: uuid.UUID,
    payload: CommentCreateRequest,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> CommentResponse:
    # 1. Verify parent task exists and belongs to caller's active organization
    stmt = (
        select(Task)
        .options(selectinload(Task.assignee), selectinload(Task.creator))
        .where(Task.id == task_id, Task.organization_id == ctx.organization_id)
    )
    task = (await db.execute(stmt)).scalar_one_or_none()
    if not task:
        raise NotFoundException(
            f"Task '{task_id}' not found in active organization.",
            code="TASK_NOT_FOUND",
        )

    # 2. Create comment
    comment = Comment(
        id=uuid.uuid4(),
        task_id=task.id,
        author_id=ctx.user_id,
        content=payload.content.strip(),
    )
    db.add(comment)

    # 3. Log activity
    await record_activity(
        db=db,
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        action="comment_created",
        target_type="task",
        target_id=task.id,
        target_title=task.title,
        project_id=task.project_id,
        details={
            "comment_id": str(comment.id),
            "task_id": str(task.id),
            "task_key": task.key,
            "snippet": comment.content[:100],
        },
    )

    # 4. Notify task assignee (if assignee is not the commenter)
    author_name = ctx.user.name or ctx.user.email
    if task.assignee_id and task.assignee_id != ctx.user_id:
        await create_notification(
            db=db,
            user_id=task.assignee_id,
            sender_id=ctx.user_id,
            type=NotificationType.MENTION,
            title=f"New comment on {task.key}",
            message=f"{author_name} commented: '{comment.content[:120]}'",
            link=f"/tasks/{task.id}",
        )

    # Notify task creator (if creator is neither assignee nor commenter)
    if (
        task.creator_id
        and task.creator_id != ctx.user_id
        and task.creator_id != task.assignee_id
    ):
        await create_notification(
            db=db,
            user_id=task.creator_id,
            sender_id=ctx.user_id,
            type=NotificationType.SYSTEM,
            title=f"New comment on {task.key}",
            message=f"{author_name} commented: '{comment.content[:120]}'",
            link=f"/tasks/{task.id}",
        )

    await db.commit()

    # Refresh comment with loaded author
    stmt_full = (
        select(Comment)
        .options(selectinload(Comment.author))
        .where(Comment.id == comment.id)
    )
    full_comment = (await db.execute(stmt_full)).scalar_one()
    return serialize_comment(full_comment)


@router.get(
    "/tasks/{task_id}/comments",
    response_model=CommentListResponse,
    summary="List Task Comments",
    description="Retrieves a paginated list of comments for a task ordered chronologically.",
)
async def list_comments(
    task_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Page offset"),
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> CommentListResponse:
    # 1. Verify task belongs to tenant organization
    task_exists = await db.scalar(
        select(Task.id).where(Task.id == task_id, Task.organization_id == ctx.organization_id)
    )
    if not task_exists:
        raise NotFoundException(
            f"Task '{task_id}' not found in active organization.",
            code="TASK_NOT_FOUND",
        )

    # 2. Count total comments
    count_stmt = select(func.count(Comment.id)).where(Comment.task_id == task_id)
    total = (await db.execute(count_stmt)).scalar() or 0

    # 3. Query paginated comments
    stmt = (
        select(Comment)
        .options(selectinload(Comment.author))
        .where(Comment.task_id == task_id)
        .order_by(Comment.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    comments = (await db.execute(stmt)).scalars().all()

    return CommentListResponse(
        items=[serialize_comment(c) for c in comments],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/comments/{comment_id}",
    response_model=CommentResponse,
    summary="Update Comment",
    description="Modifies the content of a comment. Only the author or organization Manager/Admin/Owner can edit.",
)
async def update_comment(
    comment_id: uuid.UUID,
    payload: CommentUpdateRequest,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> CommentResponse:
    stmt = (
        select(Comment)
        .join(Task, Task.id == Comment.task_id)
        .options(selectinload(Comment.author))
        .where(Comment.id == comment_id, Task.organization_id == ctx.organization_id)
    )
    comment = (await db.execute(stmt)).scalar_one_or_none()
    if not comment:
        raise NotFoundException(
            f"Comment '{comment_id}' not found in active organization.",
            code="COMMENT_NOT_FOUND",
        )

    if not can_manage_comment(ctx, comment):
        raise ForbiddenException(
            "Access denied: You do not have permission to modify this comment.",
            code="INSUFFICIENT_ROLE_PERMISSIONS",
        )

    comment.content = payload.content.strip()
    await db.commit()
    await db.refresh(comment)

    return serialize_comment(comment)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Comment",
    description="Deletes a comment. Only the author or organization Manager/Admin/Owner can delete.",
)
async def delete_comment(
    comment_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = (
        select(Comment)
        .join(Task, Task.id == Comment.task_id)
        .where(Comment.id == comment_id, Task.organization_id == ctx.organization_id)
    )
    comment = (await db.execute(stmt)).scalar_one_or_none()
    if not comment:
        raise NotFoundException(
            f"Comment '{comment_id}' not found in active organization.",
            code="COMMENT_NOT_FOUND",
        )

    if not can_manage_comment(ctx, comment):
        raise ForbiddenException(
            "Access denied: You do not have permission to delete this comment.",
            code="INSUFFICIENT_ROLE_PERMISSIONS",
        )

    await db.delete(comment)
    await db.commit()

    return {
        "status": "success",
        "message": f"Comment '{comment_id}' was successfully deleted.",
        "comment_id": str(comment_id),
    }
