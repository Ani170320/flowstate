import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException
from app.dependencies.auth import (
    ActiveOrganizationContext,
    get_active_organization,
)
from app.dependencies.database import get_db
from app.models.collaboration import Notification
from app.models.enums import NotificationType
from app.schemas.auth import UserProfileResponse
from app.schemas.collaboration import (
    NotificationBulkReadResponse,
    NotificationListResponse,
    NotificationResponse,
    NotificationUnreadCountResponse,
)

logger = logging.getLogger("flowstate.routes.notifications")

router = APIRouter(tags=["Notifications"])


def serialize_notification(n: Notification) -> NotificationResponse:
    """Serializes Notification ORM model into NotificationResponse."""
    return NotificationResponse(
        id=n.id,
        user_id=n.user_id,
        sender_id=n.sender_id,
        sender=UserProfileResponse.model_validate(n.sender) if n.sender else None,
        type=n.type,
        title=n.title,
        message=n.message,
        link=n.link,
        is_read=n.is_read,
        created_at=n.created_at,
    )


# ---------------------------------------------------------------------------
# Notifications Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/notifications",
    response_model=NotificationListResponse,
    summary="List User Notifications",
    description="Retrieves caller's notification inbox with filtering by read status and notification type.",
)
async def list_notifications(
    unread_only: bool = Query(False, description="Filter for unread alerts only"),
    type: Optional[NotificationType] = Query(None, description="Filter by notification category"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Page offset"),
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> NotificationListResponse:
    user_id = ctx.user_id

    # 1. Total unread count for user badge
    unread_stmt = select(func.count(Notification.id)).where(
        Notification.user_id == user_id,
        Notification.is_read.is_(False),
    )
    unread_count = (await db.execute(unread_stmt)).scalar() or 0

    # 2. Filtered count
    count_query = select(func.count(Notification.id)).where(Notification.user_id == user_id)
    if unread_only:
        count_query = count_query.where(Notification.is_read.is_(False))
    if type is not None:
        count_query = count_query.where(Notification.type == type)
    total = (await db.execute(count_query)).scalar() or 0

    # 3. Paginated items
    stmt = (
        select(Notification)
        .options(selectinload(Notification.sender))
        .where(Notification.user_id == user_id)
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    if type is not None:
        stmt = stmt.where(Notification.type == type)

    stmt = stmt.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
    notifications = (await db.execute(stmt)).scalars().all()

    return NotificationListResponse(
        items=[serialize_notification(n) for n in notifications],
        total=total,
        unread_count=unread_count,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/notifications/unread-count",
    response_model=NotificationUnreadCountResponse,
    summary="Get Unread Notification Count",
    description="Polls current unread count for header badge display.",
)
async def get_unread_count(
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> NotificationUnreadCountResponse:
    stmt = select(func.count(Notification.id)).where(
        Notification.user_id == ctx.user_id,
        Notification.is_read.is_(False),
    )
    count = (await db.execute(stmt)).scalar() or 0
    return NotificationUnreadCountResponse(unread_count=count)


@router.patch(
    "/notifications/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark Notification as Read",
    description="Transitions an individual notification status to read.",
)
async def mark_notification_as_read(
    notification_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    stmt = (
        select(Notification)
        .options(selectinload(Notification.sender))
        .where(Notification.id == notification_id, Notification.user_id == ctx.user_id)
    )
    notification = (await db.execute(stmt)).scalar_one_or_none()
    if not notification:
        raise NotFoundException(
            f"Notification '{notification_id}' not found in user inbox.",
            code="NOTIFICATION_NOT_FOUND",
        )

    notification.is_read = True
    await db.commit()
    await db.refresh(notification)

    return serialize_notification(notification)


@router.patch(
    "/notifications/read-all",
    response_model=NotificationBulkReadResponse,
    summary="Mark All Notifications as Read",
    description="Bulk marks all pending unread notifications as read.",
)
async def mark_all_notifications_as_read(
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> NotificationBulkReadResponse:
    stmt = (
        update(Notification)
        .where(Notification.user_id == ctx.user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    result = await db.execute(stmt)
    await db.commit()

    return NotificationBulkReadResponse(
        status="success",
        updated_count=result.rowcount or 0,
    )


@router.delete(
    "/notifications/{notification_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Notification",
    description="Removes a notification from user inbox.",
)
async def delete_notification(
    notification_id: uuid.UUID,
    ctx: ActiveOrganizationContext = Depends(get_active_organization),
    db: AsyncSession = Depends(get_db),
) -> dict:
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == ctx.user_id,
    )
    notification = (await db.execute(stmt)).scalar_one_or_none()
    if not notification:
        raise NotFoundException(
            f"Notification '{notification_id}' not found in user inbox.",
            code="NOTIFICATION_NOT_FOUND",
        )

    await db.delete(notification)
    await db.commit()

    return {
        "status": "success",
        "message": f"Notification '{notification_id}' was removed.",
        "notification_id": str(notification_id),
    }
