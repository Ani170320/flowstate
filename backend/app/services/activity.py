import logging
import uuid
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collaboration import Activity

logger = logging.getLogger("flowstate.services.activity")


async def record_activity(
    db: AsyncSession,
    organization_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    action: str,
    target_type: str,
    target_id: uuid.UUID,
    target_title: str,
    project_id: Optional[uuid.UUID] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Activity:
    """
    Appends an immutable audit activity log entry into the database.
    Does not commit directly; leaves transaction control to caller.
    """
    activity = Activity(
        id=uuid.uuid4(),
        organization_id=organization_id,
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_title=target_title[:255] if target_title else "",
        project_id=project_id,
        details=details or {},
    )
    db.add(activity)
    logger.debug(
        "Recorded activity: %s on %s:%s (org: %s, user: %s)",
        action,
        target_type,
        target_id,
        organization_id,
        user_id,
    )
    return activity
