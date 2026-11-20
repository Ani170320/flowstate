import logging
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collaboration import Notification
from app.models.enums import NotificationType

logger = logging.getLogger("flowstate.services.notification")


async def create_notification(
    db: AsyncSession,
    user_id: uuid.UUID,
    sender_id: Optional[uuid.UUID],
    type: NotificationType,
    title: str,
    message: str,
    link: Optional[str] = None,
) -> Optional[Notification]:
    """
    Dispatches an in-app notification to the recipient inbox.
    Suppresses notifications to oneself and deduplicates unread identical alerts.
    """
    # 1. Do not alert self
    if sender_id is not None and user_id == sender_id:
        return None

    # 2. Duplicate suppression: avoid generating duplicate unread notifications
    stmt = select(Notification.id).where(
        Notification.user_id == user_id,
        Notification.type == type,
        Notification.title == title,
        Notification.is_read.is_(False),
    )
    existing = await db.scalar(stmt)
    if existing:
        logger.debug(
            "Suppressed duplicate unread notification for user %s: '%s'",
            user_id,
            title,
        )
        return None

    notification = Notification(
        id=uuid.uuid4(),
        user_id=user_id,
        sender_id=sender_id,
        type=type,
        title=title[:255],
        message=message,
        link=link[:500] if link else None,
        is_read=False,
    )
    db.add(notification)
    logger.debug(
        "Created notification for user %s from %s (type=%s): %s",
        user_id,
        sender_id,
        type.value,
        title,
    )
    return notification
